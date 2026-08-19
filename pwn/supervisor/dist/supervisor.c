#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <fcntl.h>
#include <stddef.h>
#include <linux/seccomp.h>
#include <linux/filter.h>
#include <linux/audit.h>
#include <linux/unistd.h>
#include <sys/syscall.h>
#include <sys/ioctl.h>
#include <sys/prctl.h>
#include <sys/wait.h>
#include <sys/uio.h>
#include <string.h>
#include <limits.h>
#include <errno.h>
#include <stdint.h>
#include <sys/mman.h>
#include <sys/stat.h>
#include <time.h>
#include <sys/statfs.h>
#include <linux/magic.h>

#ifdef DEBUG
#define DBG(expr) \
    do            \
    {             \
        expr;     \
    } while (0)
#else
#define DBG(expr) \
    do            \
    {             \
    } while (0)
#endif

#define INIT_CAP_FD 8

int seccomp(unsigned int op, unsigned int flags, void *args)
{
    return syscall(SYS_seccomp, op, flags, args);
}

int pidfd_getfd(int pidfd, int targetfd, unsigned int flags)
{
    return syscall(SYS_pidfd_getfd, pidfd, targetfd, flags);
}

int pidfd_open(pid_t pid, unsigned int flags)
{
    return syscall(SYS_pidfd_open, pid, flags);
}

int newfstatat(int dirfd, const char *pathname, struct stat *buf, int flags)
{
    return syscall(SYS_newfstatat, dirfd, pathname, buf, flags);
}

ssize_t vm_read(pid_t pid, void *buf, size_t count, const void *remote_addr)
{
    struct iovec local = {
        .iov_base = buf,
        .iov_len = count,
    };

    struct iovec remote = {
        .iov_base = (void *)remote_addr,
        .iov_len = count,
    };

    return process_vm_readv(pid, &local, 1, &remote, 1, 0);
}

ssize_t vm_write(pid_t pid, const void *buf, size_t count, void *remote_addr)
{
    struct iovec local = {
        .iov_base = (void *)buf,
        .iov_len = count,
    };

    struct iovec remote = {
        .iov_base = remote_addr,
        .iov_len = count,
    };

    return process_vm_writev(pid, &local, 1, &remote, 1, 0);
}

typedef struct
{
    uint64_t inuse : 1;     // always set for fds being used, if unset data points to next free fd
    uint64_t is_real : 1;   // For real fds like stdin, stdout, stderr. data field will be the real fd
    uint64_t was_duped : 1; // fd has been duped
    uint64_t is_dup : 1;    // fd is a dup. data field will be the index of the original fd
    uint64_t cloexec : 1;   // close fd on exec
    uint64_t readperm : 1;
    uint64_t writeperm : 1;
    uint64_t append : 1; // O_APPEND flag
    uint64_t addfd : 1;  // fd has been added to child

    union
    {
        struct
        { // used while inuse == 1
            uint64_t data;
            uint64_t offset;
        };
        struct
        {
            uint64_t next_free;
            uint64_t prev_free;
        };
    };
} fd_sup_t;

typedef struct
{
    uint64_t size;      // Highest fd active
    uint64_t cap;       // Capacity of list
    uint64_t free_head; // first unused slot
    uint64_t free_tail;
    fd_sup_t *list;
} fd_list_t;

typedef struct
{
    char name[PATH_MAX];
    uint64_t name_hash; // for quick checking of file name
    uint64_t refcnt : 60;
    uint64_t readperm : 1;
    uint64_t writeperm : 1;
    uint64_t execperm : 1;    // not really used
    uint64_t was_written : 1; // File has been written to in which case we have to keep the on memory data alive
    uint64_t realfile : 1;    // File was based on a real file
    uint64_t size;            // File size
    uint64_t cap;             // Capacity of mapped data
    void *data;
} file_sup_t;

file_sup_t files[0x100];
fd_list_t fds = {
    .free_head = UINT64_MAX,
    .free_tail = UINT64_MAX,
    .size = 0,
    .cap = 0,
    .list = NULL};

int is_fd_slot_empty(uint64_t i)
{
    // assumes i is in bound
    return !fds.list[i].inuse;
}

int fd_list_insert(fd_sup_t *fd)
{
    uint64_t idx = -1;

    if (fds.free_head != UINT64_MAX)
    {
        idx = fds.free_head;

        fd_sup_t *free_fd = &fds.list[idx];

        // Remove from free list
        fds.free_head = free_fd->next_free;

        if (fds.free_head != UINT64_MAX)
            fds.list[fds.free_head].prev_free = UINT64_MAX;
        else
            fds.free_tail = UINT64_MAX;
    }
    else
    {
        // append
        if (fds.size >= fds.cap)
        {
            uint64_t new_cap = fds.cap ? fds.cap * 2 : INIT_CAP_FD;

            fds.list = realloc(fds.list, new_cap * sizeof(fd_sup_t));
            fds.cap = new_cap;
        }

        idx = fds.size;
        fds.size++;
    }

    fds.list[idx] = *fd;
    fds.list[idx].inuse = 1;
    return idx;
}

int fd_list_insert_at(uint64_t idx, const fd_sup_t *fd)
{
    if (idx >= fds.cap)
    {
        uint64_t new_cap = fds.cap ? fds.cap * 2 : INIT_CAP_FD;

        while (new_cap <= idx)
            new_cap *= 2;

        fds.list = realloc(fds.list, new_cap * sizeof(fd_sup_t));
        fds.cap = new_cap;
    }

    // If inserting past current size, initialize the gap as free slots.
    if (idx >= fds.size)
    {
        uint64_t old_size = fds.size;

        for (uint64_t i = old_size; i < idx; i++)
        {
            fd_sup_t *e = &fds.list[i];

            memset(e, 0, sizeof(*e));
            e->inuse = 0;

            e->next_free = UINT64_MAX;
            e->prev_free = fds.free_tail;

            if (fds.free_tail != UINT64_MAX)
                fds.list[fds.free_tail].next_free = i;
            else
                fds.free_head = i;

            fds.free_tail = i;
        }

        fds.size = idx + 1;
    }
    else
    {
        // idx is an existing slot. If it is free,
        // remove it from the free list.
        fd_sup_t *e = &fds.list[idx];

        if (!e->inuse)
        {
            if (e->prev_free != UINT64_MAX)
                fds.list[e->prev_free].next_free = e->next_free;
            else
                fds.free_head = e->next_free;

            if (e->next_free != UINT64_MAX)
                fds.list[e->next_free].prev_free = e->prev_free;
            else
                fds.free_tail = e->prev_free;
        }
    }

    fds.list[idx] = *fd;
    fds.list[idx].inuse = 1;

    return idx;
}

void fd_free_remove(uint64_t fd)
{
    fd_sup_t *e = &fds.list[fd];

    if (e->prev_free != UINT64_MAX)
        fds.list[e->prev_free].next_free = e->next_free;
    else
        fds.free_head = e->next_free;

    if (e->next_free != UINT64_MAX)
        fds.list[e->next_free].prev_free = e->prev_free;
    else
        fds.free_tail = e->prev_free;

    e->next_free = UINT64_MAX;
    e->prev_free = UINT64_MAX;
}

char *u64_to_hex(uint64_t value, char *out)
{
    static const char hex[] = "0123456789abcdef";

    for (int i = 15; i >= 0; i--)
    {
        out[i] = hex[value & 0xf];
        value >>= 4;
    }

    out[16] = '\0';
    return out;
}

uint64_t hash_string(const char *str)
{
    uint64_t hash = 14695981039346656037ULL;

    while (*str)
    {
        hash ^= (uint8_t)*str++;
        hash *= 1099511628211ULL;
    }

    return hash;
}

int is_file_slot_empty(int i)
{
    // if file has ever been written to we will have to keep track of it forever
    return i < 0x100 && files[i].refcnt == 0 && files[i].was_written == 0;
}

int search_file(const char *pathname)
{
    uint64_t hash = hash_string(pathname);
    int file_idx = -1;
    for (size_t i = 0; i < 0x100; i++)
    {
        if (is_file_slot_empty(i))
            continue;

        if (files[i].name_hash == hash && strncmp(pathname, files[i].name, PATH_MAX) == 0)
        {
            file_idx = i;
            break;
        }
    }

    return file_idx;
}

int search_file_empty()
{
    int file_idx = -1;
    for (size_t i = 0; i < 0x100; i++)
    {
        if (is_file_slot_empty(i))
        {
            file_idx = i;
            break;
        }
    }

    return file_idx;
}

int create_existing(const char *pathname)
{
    struct stat st;
    struct statfs fs;
    if (stat(pathname, &st) != 0 || !S_ISREG(st.st_mode) || statfs(pathname, &fs) != 0 || fs.f_type == PROC_SUPER_MAGIC)
    {
        return -1;
    }
    int file_id = search_file_empty();
    if (file_id == -1)
        return -1;

    memset(&files[file_id], 0, sizeof(files[file_id]));
    strncpy(files[file_id].name, pathname, PATH_MAX);
    files[file_id].readperm = !!(st.st_mode & S_IROTH);
    files[file_id].writeperm = !!(st.st_mode & S_IWOTH);
    files[file_id].execperm = !!(st.st_mode & S_IXOTH);
    files[file_id].realfile = 1;
    files[file_id].name_hash = hash_string(pathname);
    files[file_id].size = st.st_size;
    files[file_id].cap = (st.st_size + 0x1000 - 1) & ~(0x1000 - 1);
    int file_fd = open(pathname, O_RDONLY);
    files[file_id].data = mmap(NULL, files[file_id].cap, PROT_READ | PROT_WRITE, MAP_PRIVATE, file_fd, 0);
    close(file_fd);
    if (files[file_id].data == MAP_FAILED)
    {
        return -1;
    }

    return file_id;
}

int create_empty(const char *pathname, int r, int w, int x)
{
    struct stat st;
    if (stat(pathname, &st) == 0)
    {
        return -1;
    }
    int file_id = search_file_empty();
    if (file_id == -1)
        return -1;

    memset(&files[file_id], 0, sizeof(files[file_id]));
    strncpy(files[file_id].name, pathname, PATH_MAX);

    files[file_id].readperm = r;
    files[file_id].writeperm = w;
    files[file_id].execperm = x;
    files[file_id].name_hash = hash_string(pathname);
    files[file_id].realfile = 0;
    files[file_id].was_written = 1;
    files[file_id].size = 0;
    files[file_id].cap = 0x1000;
    files[file_id].data = mmap(NULL, files[file_id].cap, PROT_READ | PROT_WRITE, MAP_PRIVATE | MAP_ANONYMOUS, 0, 0);
    return file_id;
}

int is_open_allowed(file_sup_t *file, int flags)
{
    switch (flags & O_ACCMODE)
    {
    case O_RDONLY:
        return file->readperm;

    case O_WRONLY:
        return file->writeperm;

    case O_RDWR:
        return file->readperm && file->writeperm;

    default:
        return 0;
    }
}

int sup_open(pid_t pid, char *pathname, int flags, int mode)
{
    int file_id = search_file(pathname);
    if (file_id == -1)
    {
        struct stat st;
        if (stat(pathname, &st) == 0)
        {
            file_id = create_existing(pathname);
            if (file_id < 0)
            {
                return file_id;
            }
        }
        else if (flags & O_CREAT)
        {
            file_id = create_empty(pathname, !!(mode & 4), !!(mode & 2), !!(mode & 1));
            if (file_id < 0)
            {
                return file_id;
            }
        }
        else
        {
            return -ENOENT;
        }
    }

    if (!is_open_allowed(&files[file_id], flags))
    {
        return -EPERM;
    }

    if (flags & O_TRUNC && ((flags & O_ACCMODE) == O_WRONLY || (flags & O_ACCMODE) == O_RDWR))
    {
        files[file_id].size = 0;
    }

    files[file_id].refcnt += 1;

    fd_sup_t fd = {0};
    fd.inuse = 1;
    fd.data = file_id;
    switch (flags & O_ACCMODE)
    {
    case O_RDONLY:
        fd.readperm = 1;
        break;

    case O_WRONLY:
        fd.writeperm = 1;
        break;

    case O_RDWR:
        fd.readperm = 1;
        fd.writeperm = 1;
        break;
    }
    fd.cloexec = !!(flags & O_CLOEXEC);
    fd.append = !!(flags & O_APPEND);

    return fd_list_insert(&fd);
}

// returns -1 if there is no file associated (fd has is_real set)
int get_fileid_fd(int fd)
{
    if (fds.list[fd].is_dup)
    {
        if (fds.list[fds.list[fd].data].is_real)
            return -1;

        return fds.list[fds.list[fd].data].data;
    }
    if (fds.list[fd].is_real)
        return -1;

    return fds.list[fd].data;
}

void sup_file_dec_refcnt(int fileid)
{
    files[fileid].refcnt--;
    if (!is_file_slot_empty(fileid))
        return;

    if (files[fileid].data)
    {
        munmap(files[fileid].data, files[fileid].cap);
    }
}

int sup_close(int pid, int fd)
{
    if (fd < 0 || fd > fds.size || fds.list[fd].inuse == 0)
        return -EBADF;

    int fileid = get_fileid_fd(fd);
    if (fileid != -1)
        sup_file_dec_refcnt(fileid);

    // if file was duped we need to search through the list to fix dup pointers
    if (fds.list[fd].was_duped)
    {
        int first = -1;
        for (size_t i = 0; i < fds.size; i++)
        {
            if (!fds.list[i].inuse || !fds.list[i].is_dup || fds.list[i].data != fd)
                continue;

            if (first == -1)
            {
                first = i;
                int addfd = fds.list[i].addfd;
                fds.list[i] = fds.list[fd];
                fds.list[i].addfd = addfd;
            }
            else
            {
                fds.list[i].data = first;
            }
        }
    }
    fds.list[fd].inuse = 0;
    if (fd == fds.size)
    {
        while (fds.list[fds.size].inuse == 0)
        {
            fd_free_remove(fds.size);
            fds.size--;
        }
        return 0;
    }

    fds.list[fd].prev_free = UINT64_MAX;
    fds.list[fd].next_free = fds.free_head;
    if (fds.free_head != UINT64_MAX)
        fds.list[fds.free_head].prev_free = fd;
    else
        fds.free_tail = fd;
    fds.free_head = fd;

    return 0;
}

char *resolve_path(const char *path, char *out)
{
    char abs[PATH_MAX] = {0};
    char tmp[PATH_MAX] = {0};

    if (path == NULL)
    {
        errno = EINVAL;
        return NULL;
    }

    // Make path absolute.
    if (path[0] == '/')
    {
        if (strlen(path) >= PATH_MAX)
        {
            return NULL;
        }

        strcpy(abs, path);
    }
    else
    {
        if (getcwd(abs, sizeof(abs)) == NULL)
            return NULL;

        size_t len = strlen(abs);

        if (len + 1 + strlen(path) + 1 > PATH_MAX)
        {
            return NULL;
        }

        if (len && abs[len - 1] != '/')
            abs[len++] = '/';

        strcpy(abs + len, path);
    }

    strcpy(tmp, abs);

    while (1)
    {
        char resolved[PATH_MAX];

        if (realpath(tmp, resolved))
        {
            size_t prefix_len = strlen(tmp);

            if (strlen(resolved) >= PATH_MAX)
            {
                return NULL;
            }

            strcpy(out, resolved);

            if (abs[prefix_len] != '\0')
            {
                size_t out_len = strlen(out);

                if (out[out_len - 1] != '/')
                {
                    if (out_len + 1 >= PATH_MAX)
                    {
                        return NULL;
                    }

                    out[out_len++] = '/';
                    out[out_len] = '\0';
                }

                const char *suffix = abs + prefix_len + 1;

                if (out_len + strlen(suffix) + 1 > PATH_MAX)
                {
                    return NULL;
                }

                strcat(out, suffix);
            }

            return out;
        }

        if (errno != ENOENT)
            return NULL;

        char *slash = strrchr(tmp, '/');

        if (slash == NULL)
            return NULL;

        if (slash == tmp)
        {
            tmp[1] = '\0';
        }
        else
        {
            *slash = '\0';
        }
    }
}

int read_path(pid_t pid, void *pathname_child, char *pathname)
{
    char tmp_path[PATH_MAX] = {0};
    if (vm_read(pid, tmp_path, PATH_MAX, pathname_child) == 0)
        return -1;

    char *res = resolve_path(tmp_path, pathname);
    if (res == NULL)
        return -1;
    return 0;
}

int fill_stat(const char *pathname, struct stat *st)
{
    int fileid = search_file(pathname);
    if (fileid == -1)
    {
        return newfstatat(AT_FDCWD, pathname, st, 0);
    }

    if (files[fileid].realfile)
    {
        newfstatat(AT_FDCWD, pathname, st, 0);
        st->st_size = files[fileid].size;
        return 0;
    }

    memset(st, 0, sizeof(*st));
    st->st_dev = 1;
    st->st_rdev = 0;
    st->st_ino = files[fileid].name_hash;
    st->st_mode = S_IFREG;

    if (files[fileid].readperm)
        st->st_mode |= S_IRUSR | S_IRGRP | S_IROTH;

    if (files[fileid].writeperm)
        st->st_mode |= S_IWUSR | S_IWGRP | S_IWOTH;

    if (files[fileid].execperm)
        st->st_mode |= S_IXUSR | S_IXGRP | S_IXOTH;
    st->st_nlink = 1;
    st->st_uid = 100000;
    st->st_gid = 100000;
    st->st_blksize = 4096;
    st->st_blocks = (files[fileid].size + 511) / 512;
    time_t now = time(NULL);
    st->st_atim.tv_sec = now;
    st->st_mtim.tv_sec = now;
    st->st_ctim.tv_sec = now;
    st->st_atim.tv_nsec = 0;
    st->st_mtim.tv_nsec = 0;
    st->st_ctim.tv_nsec = 0;
    return 0;
}

ssize_t write_fd(pid_t pid, fd_sup_t *fd, void *buf, size_t count, size_t offset_given, int update_offset)
{
    if (fd->is_dup)
    {
        fd = &fds.list[fd->data];
    }

    if (fd->writeperm == 0)
    {
        return -EPERM;
    }

    if (fd->is_real)
    {
        size_t tot_written = 0;
        char buf_tmp[0x1000];
        while (count)
        {
            int cnt_read = vm_read(pid, buf_tmp, (count > 0x1000) ? 0x1000 : count, buf);
            if (cnt_read == 0)
                break;
            write(fd->data, buf_tmp, cnt_read);
            count -= cnt_read;
            buf += cnt_read;
            tot_written += cnt_read;
        }

        return tot_written;
    }

    int fileid = fd->data;
    size_t offset = fd->append ? files[fileid].size : fd->offset;
    if (offset_given != UINT64_MAX)
        offset = offset_given;

    if (offset + count > files[fileid].cap)
    {
        size_t tmp_cap = files[fileid].cap;
        files[fileid].cap = ((offset + count) + 0x1000 - 1) & ~(0x1000 - 1);
        files[fileid].data = mremap(files[fileid].data, tmp_cap, files[fileid].cap, MREMAP_MAYMOVE);
    }

    size_t res = vm_read(pid, files[fileid].data + offset, count, buf);
    if (offset + res > files[fileid].size)
        files[fileid].size = offset + res;
    if (update_offset)
        fd->offset = offset + res;
    return res;
}

ssize_t read_fd(pid_t pid, fd_sup_t *fd, void *buf, size_t count, size_t offset_given, int update_offset)
{
    if (fd->is_dup)
    {
        fd = &fds.list[fd->data];
    }

    if (fd->readperm == 0)
    {
        return -EPERM;
    }

    if (fd->is_real)
    {
        size_t tot_read = 0;
        char buf_tmp[0x1000];
        while (count)
        {
            size_t read_block_count = (count > 0x1000) ? 0x1000 : count;
            size_t cnt_read = read(fd->data, buf_tmp, read_block_count);
            if (cnt_read == 0)
                break;
            size_t cnt_read2 = vm_write(pid, buf_tmp, cnt_read, buf);
            if (cnt_read2 != cnt_read)
                break;
            count -= cnt_read;
            buf += cnt_read;
            tot_read += cnt_read2;
            if (cnt_read != read_block_count)
                break;
        }

        return tot_read;
    }

    int fileid = fd->data;
    size_t offset = fd->append ? files[fileid].size : fd->offset;
    if (offset_given != UINT64_MAX)
        offset = offset_given;
    if (offset + count > files[fileid].size)
    {
        count = files[fileid].size - offset;
    }
    size_t res = vm_write(pid, files[fileid].data + offset, count, buf);
    if (update_offset)
        fd->offset = offset + res;
    return res;
}

void init_sup()
{
    // init stdin, stdout, stderr
    fd_sup_t stdin_sup = {0};
    stdin_sup.inuse = 1;
    stdin_sup.is_real = 1;
    stdin_sup.readperm = 1;
    stdin_sup.data = STDIN_FILENO;
    fd_list_insert(&stdin_sup);

    fd_sup_t stdout_sup = {0};
    stdout_sup.inuse = 1;
    stdout_sup.is_real = 1;
    stdout_sup.writeperm = 1;
    stdout_sup.data = STDOUT_FILENO;
    fd_list_insert(&stdout_sup);

    fd_sup_t stderr_sup = {0};
    stderr_sup.inuse = 1;
    stderr_sup.is_real = 1;
    stderr_sup.writeperm = 1;
    stderr_sup.data = STDERR_FILENO;
    fd_list_insert(&stderr_sup);
}

void supervisor(int listener, pid_t pid, int pidfd)
{
    struct seccomp_notif *req;
    struct seccomp_notif_resp *resp;
    struct seccomp_notif_sizes sizes;

    if (seccomp(SECCOMP_GET_NOTIF_SIZES, 0, &sizes))
    {
        perror("GET_NOTIF_SIZES");
        return;
    }

    req = alloca(sizes.seccomp_notif);
    resp = alloca(sizes.seccomp_notif_resp);

    fd_set fdset;
    int maxfd = (listener > pidfd) ? listener : pidfd;
    while (1)
    {
        FD_ZERO(&fdset);
        FD_SET(listener, &fdset);
        FD_SET(pidfd, &fdset);
        int n = select(maxfd + 1, &fdset, NULL, NULL, NULL);
        if (n < 0)
        {
            perror("select");
            return;
        }

        if (FD_ISSET(pidfd, &fdset))
        {
            int status;
            waitpid(pid, &status, 0);
            return;
        }

        if (!FD_ISSET(listener, &fdset))
        {
            continue;
        }

        memset(req, 0, sizes.seccomp_notif);
        if (ioctl(listener, SECCOMP_IOCTL_NOTIF_RECV, req) < 0)
            break;

        DBG(printf("pid=%d syscall=%d\n", req->pid, req->data.nr));
        DBG(printf("args arg0=%p arg1=%p arg2=%p arg3=%p arg4=%p arg5=%p\n", req->data.args[0], req->data.args[1], req->data.args[2], req->data.args[3], req->data.args[4], req->data.args[5]));

        memset(resp, 0, sizes.seccomp_notif_resp);
        resp->id = req->id;

        switch (req->data.nr)
        {
        case __NR_open:
        {
            char pathname[PATH_MAX];
            if (read_path(pid, (void *)req->data.args[0], pathname) == -1)
            {
                resp->flags = 0;
                resp->val = 0;
                resp->error = -EINVAL;
                break;
            }

            int fd = sup_open(pid, pathname, req->data.args[1], req->data.args[2]);
            if (fd < 0)
            {
                resp->flags = 0;
                resp->val = 0;
                resp->error = fd;
                break;
            }
            resp->flags = 0;
            resp->val = fd;
            resp->error = 0;
        }
        break;

        case __NR_openat:
        {
            // We dont allow opening directory fds.
            if ((int)req->data.args[0] != AT_FDCWD)
            {
                resp->flags = 0;
                resp->val = 0;
                resp->error = -ENOTDIR;
                break;
            }
            char pathname[PATH_MAX];
            if (read_path(pid, (void *)req->data.args[1], pathname) == -1)
            {
                resp->flags = 0;
                resp->val = 0;
                resp->error = -EINVAL;
                break;
            }

            int fd = sup_open(pid, pathname, req->data.args[2], req->data.args[3]);
            if (fd < 0)
            {
                resp->flags = 0;
                resp->val = 0;
                resp->error = fd;
                break;
            }
            resp->flags = 0;
            resp->val = fd;
            resp->error = 0;
        }
        break;

        case __NR_close:
        {
            int res = sup_close(pid, req->data.args[0]);
            if (res < 0)
            {
                resp->flags = 0;
                resp->val = 0;
                resp->error = res;
                break;
            }
            resp->flags = 0;
            resp->val = res;
            resp->error = 0;
        }
        break;

        case __NR_execve:
            for (size_t i = 0; i < fds.size; i++)
            {
                if (fds.list[i].inuse == 0 || fds.list[i].cloexec == 0)
                    continue;
                sup_close(pid, i);
            }
            resp->flags = SECCOMP_USER_NOTIF_FLAG_CONTINUE;
            resp->val = 0;
            resp->error = 0;
            break;

        case __NR_mmap:
        {
            int flag = req->data.args[3];
            int fd = req->data.args[4];
            if (flag & MAP_SHARED)
            {
                resp->flags = 0;
                resp->val = 0;
                resp->error = -EINVAL;
                break;
            }

            if (!(flag & MAP_ANONYMOUS))
            {
                if (fd < 0 || fd > fds.size || fds.list[fd].inuse == 0)
                {
                    resp->flags = 0;
                    resp->val = 0;
                    resp->error = -EBADF;
                    break;
                }
                int file_id = get_fileid_fd(fd);
                if (file_id == -1)
                {
                    resp->flags = 0;
                    resp->val = 0;
                    resp->error = -EACCES;
                    break;
                }
                int real_fd;
                int setaddfd = 0;
                if (files[file_id].was_written || !files[file_id].realfile)
                {
                    char tmp_name[0x20] = "/tmp/";
                    u64_to_hex(files[file_id].name_hash, tmp_name + 5);
                    real_fd = open(tmp_name, O_TRUNC | O_WRONLY | O_CREAT, 0400);
                    write(real_fd, files[file_id].data, files[file_id].size);
                    fchmod(real_fd, 0666);
                    close(real_fd);
                    real_fd = open(tmp_name, O_RDONLY);
                    setaddfd = 1;
                }
                else
                {
                    real_fd = open(files[file_id].name, O_RDONLY);
                }
                if (fds.list[fd].addfd == 0)
                {
                    struct seccomp_notif_addfd addfd;
                    addfd.id = req->id;
                    addfd.flags = SECCOMP_ADDFD_FLAG_SETFD;
                    addfd.srcfd = real_fd;
                    addfd.newfd = fd;
                    addfd.newfd_flags = fds.list[fd].cloexec ? O_CLOEXEC : 0;
                    fds.list[fd].addfd = setaddfd;

                    if (ioctl(listener, SECCOMP_IOCTL_NOTIF_ADDFD, &addfd) < 0)
                    {
                        perror("NOTIF_SEND");
                    }
                }
                close(real_fd);
            }

            resp->flags = SECCOMP_USER_NOTIF_FLAG_CONTINUE;
            resp->val = 0;
            resp->error = 0;
        }
        break;

        case __NR_newfstatat:
        {
            int dirfd = req->data.args[0];
            struct stat *child_stat = (struct stat *)req->data.args[2];
            int flags = req->data.args[3];

            struct stat st = {0};

            char pathname[PATH_MAX];
            if (vm_read(pid, pathname, 1, (void *)req->data.args[1]) != 1 || (pathname[0] != '\0' && read_path(pid, (void *)req->data.args[1], pathname) == -1))
            {
                resp->flags = 0;
                resp->val = 0;
                resp->error = -EINVAL;
                break;
            }

            if ((flags & AT_EMPTY_PATH) && pathname[0] == '\0')
            {
                if (dirfd < 0 || dirfd > fds.size || fds.list[dirfd].inuse == 0)
                {
                    resp->flags = 0;
                    resp->val = 0;
                    resp->error = -EBADF;
                    break;
                }

                int fileid = get_fileid_fd(dirfd);
                if (fileid == -1)
                {
                    // this means fd or its dup has is_real set
                    if (fds.list[dirfd].is_dup)
                        dirfd = fds.list[dirfd].data;

                    int res = newfstatat(fds.list[dirfd].data, "", &st, AT_EMPTY_PATH);
                    if (res < 0)
                    {
                        resp->flags = 0;
                        resp->val = 0;
                        resp->error = res;
                        break;
                    }

                    vm_write(pid, &st, sizeof(st), child_stat);
                    resp->flags = 0;
                    resp->val = 0;
                    resp->error = 0;
                    break;
                }

                int res = fill_stat(files[fileid].name, &st);
                if (res < 0)
                {
                    resp->flags = 0;
                    resp->val = 0;
                    resp->error = res;
                    break;
                }
                vm_write(pid, &st, sizeof(st), child_stat);
                resp->flags = 0;
                resp->val = res;
                resp->error = 0;
                break;
            }
            int res = fill_stat(pathname, &st);
            if (res < 0)
            {
                resp->flags = 0;
                resp->val = 0;
                resp->error = res;
                break;
            }
            vm_write(pid, &st, sizeof(st), child_stat);
            resp->flags = 0;
            resp->val = res;
            resp->error = 0;
            break;
        }
        break;

        case __NR_fstat:
        {
            int fd = req->data.args[0];
            struct stat *child_stat = (struct stat *)req->data.args[1];

            struct stat st = {0};

            if (fd < 0 || fd > fds.size || fds.list[fd].inuse == 0)
            {
                resp->flags = 0;
                resp->val = 0;
                resp->error = -EBADF;
                break;
            }

            int fileid = get_fileid_fd(fd);
            if (fileid == -1)
            {
                // this means fd or its dup has is_real set
                if (fds.list[fd].is_dup)
                    fd = fds.list[fd].data;

                int res = newfstatat(fds.list[fd].data, "", &st, AT_EMPTY_PATH);
                if (res < 0)
                {
                    resp->flags = 0;
                    resp->val = 0;
                    resp->error = res;
                    break;
                }

                vm_write(pid, &st, sizeof(st), child_stat);
                resp->flags = 0;
                resp->val = 0;
                resp->error = 0;
                break;
            }

            int res = fill_stat(files[fileid].name, &st);
            if (res < 0)
            {
                resp->flags = 0;
                resp->val = 0;
                resp->error = res;
                break;
            }
            vm_write(pid, &st, sizeof(st), child_stat);
            resp->flags = 0;
            resp->val = res;
            resp->error = 0;
        }
        break;

        case __NR_write:
        {
            int fd = req->data.args[0];
            void *child_buf = (void *)req->data.args[1];
            size_t count = req->data.args[2];
            if (fd < 0 || fd > fds.size || fds.list[fd].inuse == 0)
            {
                resp->flags = 0;
                resp->val = 0;
                resp->error = -EBADF;
                break;
            }

            if (fds.list[fd].writeperm == 0)
            {
                resp->flags = 0;
                resp->val = 0;
                resp->error = -EPERM;
                break;
            }

            ssize_t res = write_fd(pid, &fds.list[fd], child_buf, count, UINT64_MAX, 1);

            if (res < 0L)
            {
                resp->flags = 0;
                resp->val = 0;
                resp->error = res;
                break;
            }

            resp->flags = 0;
            resp->val = res;
            resp->error = 0;
            break;
        }
        break;

        case __NR_pwrite64:
        {
            int fd = req->data.args[0];
            void *child_buf = (void *)req->data.args[1];
            size_t count = req->data.args[2];
            size_t offset = req->data.args[3];
            if (fd < 0 || fd > fds.size || fds.list[fd].inuse == 0)
            {
                resp->flags = 0;
                resp->val = 0;
                resp->error = -EBADF;
                break;
            }

            if (fds.list[fd].writeperm == 0)
            {
                resp->flags = 0;
                resp->val = 0;
                resp->error = -EPERM;
                break;
            }

            ssize_t res = write_fd(pid, &fds.list[fd], child_buf, count, offset, 0);

            if (res < 0L)
            {
                resp->flags = 0;
                resp->val = 0;
                resp->error = res;
                break;
            }

            resp->flags = 0;
            resp->val = res;
            resp->error = 0;
            break;
        }
        break;

        case __NR_writev:
        {
            int fd = req->data.args[0];
            void *iov = (void *)req->data.args[1];
            int iovcnt = req->data.args[2];
            if (fd < 0 || fd > fds.size || fds.list[fd].inuse == 0)
            {
                resp->flags = 0;
                resp->val = 0;
                resp->error = -EBADF;
                break;
            }

            if (fds.list[fd].writeperm == 0)
            {
                resp->flags = 0;
                resp->val = 0;
                resp->error = -EPERM;
                break;
            }

            ssize_t tot_write = 0;
            for (size_t i = 0; i < iovcnt; i++)
            {
                struct iovec vec;
                if (vm_read(pid, &vec, sizeof(vec), iov + (sizeof(vec) * i)) == 0)
                {
                    break;
                }
                ssize_t res = write_fd(pid, &fds.list[fd], vec.iov_base, vec.iov_len, UINT64_MAX, 1);
                if (res < 0L)
                {
                    tot_write = res;
                    break;
                }
                tot_write += res;
            }

            if (tot_write < 0)
            {
                resp->flags = 0;
                resp->val = 0;
                resp->error = tot_write;
                break;
            }
            resp->flags = 0;
            resp->val = tot_write;
            resp->error = 0;
        }
        break;

        case __NR_read:
        {
            int fd = req->data.args[0];
            void *child_buf = (void *)req->data.args[1];
            size_t count = req->data.args[2];
            DBG(printf("read %p, %p, %p\n", fd, child_buf, count));
            if (fd < 0 || fd > fds.size || fds.list[fd].inuse == 0)
            {
                resp->flags = 0;
                resp->val = 0;
                resp->error = -EBADF;
                break;
            }

            ssize_t res = read_fd(pid, &fds.list[fd], child_buf, count, UINT64_MAX, 1);
            if (res < 0L)
            {
                resp->flags = 0;
                resp->val = 0;
                resp->error = res;
                break;
            }

            resp->flags = 0;
            resp->val = res;
            resp->error = 0;
        }
        break;

        case __NR_pread64:
        {
            int fd = req->data.args[0];
            void *child_buf = (void *)req->data.args[1];
            size_t count = req->data.args[2];
            size_t offset = req->data.args[3];
            if (fd < 0 || fd > fds.size || fds.list[fd].inuse == 0)
            {
                resp->flags = 0;
                resp->val = 0;
                resp->error = -EBADF;
                break;
            }

            if (fds.list[fd].readperm == 0)
            {
                resp->flags = 0;
                resp->val = 0;
                resp->error = -EPERM;
                break;
            }

            ssize_t res = read_fd(pid, &fds.list[fd], child_buf, count, offset, 0);
            if (res < 0L)
            {
                resp->flags = 0;
                resp->val = 0;
                resp->error = res;
                break;
            }

            resp->flags = 0;
            resp->val = res;
            resp->error = 0;
            break;
        }
        break;

        case __NR_dup:
        {
            int fd = req->data.args[0];

            if (fd < 0 || fd > fds.size || fds.list[fd].inuse == 0)
            {
                resp->flags = 0;
                resp->val = 0;
                resp->error = -EBADF;
                break;
            }

            if (fds.list[fd].is_dup)
            {
                fd = fds.list[fd].data;
            }

            fd_sup_t newfd = {0};
            newfd.inuse = 1;
            newfd.is_dup = 1;
            newfd.data = fd;

            fds.list[fd].was_duped = 1;

            resp->flags = 0;
            resp->val = fd_list_insert(&newfd);
            resp->error = 0;
        }
        break;

        case __NR_dup2:
        {
            int fd = req->data.args[0];
            int newfd_id = req->data.args[1];

            if (fd < 0 || fd > fds.size || fds.list[fd].inuse == 0 || newfd_id < 0)
            {
                resp->flags = 0;
                resp->val = 0;
                resp->error = -EBADF;
                break;
            }

            if (fds.list[fd].is_dup)
            {
                fd = fds.list[fd].data;
            }

            fd_sup_t newfd = {0};
            newfd.inuse = 1;
            newfd.is_dup = 1;
            newfd.data = fd;

            fds.list[fd].was_duped = 1;

            // if newfd is inuse we need to close it first
            if (newfd_id < fds.size && fds.list[newfd_id].inuse)
            {
                sup_close(pid, newfd_id);
            }

            resp->flags = 0;
            resp->val = fd_list_insert_at(newfd_id, &newfd);
            resp->error = 0;
        }
        break;

        case __NR_dup3:
        {
            int fd = req->data.args[0];
            int newfd_id = req->data.args[1];
            int flags = req->data.args[2];

            if (fd < 0 || fd > fds.size || fds.list[fd].inuse == 0 || newfd_id < 0)
            {
                resp->flags = 0;
                resp->val = 0;
                resp->error = -EBADF;
                break;
            }

            // spec doesnt allow same fd and newfd
            if (newfd_id == fd)
            {
                resp->flags = 0;
                resp->val = 0;
                resp->error = -EINVAL;
                break;
            }

            if (fds.list[fd].is_dup)
            {
                fd = fds.list[fd].data;
            }

            fd_sup_t newfd = {0};
            newfd.inuse = 1;
            newfd.is_dup = 1;
            newfd.data = fd;
            newfd.cloexec = !!(flags & O_CLOEXEC);

            fds.list[fd].was_duped = 1;

            // if newfd is inuse we need to close it first
            if (newfd_id < fds.size && fds.list[newfd_id].inuse)
            {
                sup_close(pid, newfd_id);
            }

            resp->flags = 0;
            resp->val = fd_list_insert_at(newfd_id, &newfd);
            resp->error = 0;
        }
        break;

        case __NR_lseek:
        {
            int fd = req->data.args[0];
            off_t offset = req->data.args[1];
            int whence = req->data.args[2];

            if (fd < 0 || fd > fds.size || fds.list[fd].inuse == 0)
            {
                resp->flags = 0;
                resp->val = 0;
                resp->error = -EBADF;
                break;
            }

            if (fds.list[fd].is_dup)
            {
                fd = fds.list[fd].data;
            }

            int fileid = get_fileid_fd(fd);
            if (fileid == -1)
            {
                resp->flags = 0;
                resp->val = 0;
                resp->error = -ESPIPE;
                break;
            }

            if (whence == SEEK_SET)
            {
                fds.list[fd].offset = offset;
            }
            else if (whence == SEEK_CUR)
            {
                fds.list[fd].offset += offset;
            }
            else if (whence == SEEK_END)
            {
                fds.list[fd].offset = files[fileid].size + offset;
            }
            else
            {
                resp->flags = 0;
                resp->val = 0;
                resp->error = -EINVAL;
                break;
            }
            resp->flags = 0;
            resp->val = fds.list[fd].offset;
            resp->error = 0;
        }
        break;

        case __NR_access:
        {
            char pathname[PATH_MAX];
            if (read_path(pid, (void *)req->data.args[0], pathname) == -1)
            {
                resp->flags = 0;
                resp->val = 0;
                resp->error = -EINVAL;
                break;
            }
            int mode = req->data.args[1];
            if (mode == F_OK)
            {
                if (search_file(pathname) == -1 && access(pathname, F_OK) == -1)
                {
                    resp->flags = 0;
                    resp->val = 0;
                    resp->error = -EACCES;
                    break;
                }
                resp->flags = 0;
                resp->val = 0;
                resp->error = 0;
                break;
            }
            int fileid = search_file(pathname);
            if (fileid == -1)
            {
                if (search_file(pathname) == -1 && access(pathname, mode) == -1)
                {
                    resp->flags = 0;
                    resp->val = 0;
                    resp->error = -EACCES;
                    break;
                }
                resp->flags = 0;
                resp->val = 0;
                resp->error = 0;
                break;
            }

            if ((mode & R_OK) && files[fileid].readperm == 0)
            {
                resp->flags = 0;
                resp->val = 0;
                resp->error = -EACCES;
                break;
            }
            if ((mode & W_OK) && files[fileid].writeperm == 0)
            {
                resp->flags = 0;
                resp->val = 0;
                resp->error = -EACCES;
                break;
            }
            if ((mode & X_OK) && files[fileid].execperm == 0)
            {
                resp->flags = 0;
                resp->val = 0;
                resp->error = -EACCES;
                break;
            }
            resp->flags = 0;
            resp->val = 0;
            resp->error = 0;
        }
        break;

        case __NR_fadvise64:
            resp->flags = 0;
            resp->val = 0;
            resp->error = 0;
            break;

        case __NR_getpid:
            resp->flags = 0;
            resp->val = 1;
            resp->error = 0;
            break;

        case __NR_getuid:
        case __NR_geteuid:
        case __NR_getgid:
        case __NR_getegid:
            resp->flags = 0;
            resp->val = 100000;
            resp->error = 0;
            break;

        // Just continute executing. Surely nothing can go wrong.
        case __NR_exit:
        case __NR_exit_group:
        case __NR_mprotect:
        case __NR_munmap:
        case __NR_brk:
        case __NR_arch_prctl:
        case __NR_set_tid_address:
        case __NR_set_robust_list:
        case __NR_prlimit64:
        case __NR_getrandom:
        case __NR_rseq:
            resp->flags = SECCOMP_USER_NOTIF_FLAG_CONTINUE;
            resp->val = 0;
            resp->error = 0;
            break;

        // by default syscall not implemented
        default:
            resp->flags = 0;
            resp->val = 0;
            resp->error = -ENOSYS;
            break;
        }

        DBG(printf("resp flags=%d val=%d error=%d\n", resp->flags, resp->val, resp->error));

        if (ioctl(listener, SECCOMP_IOCTL_NOTIF_SEND, resp) < 0)
        {
            perror("NOTIF_SEND");
            break;
        }
    }
}

void init()
{
    setbuf(stdout, NULL);
    setbuf(stderr, NULL);
}

int get_file(char *path_out)
{
    char path[] = "/tmp/supervisorexecXXXXXX";
    int fd = mkstemp(path);
    char buf[0x1000];
    size_t total = 0;
    while (total < 0x10000)
    {
        size_t remaining = 0x10000 - total;
        size_t to_read = remaining < 0x1000 ? remaining : 0x1000;

        ssize_t n = read(STDIN_FILENO, buf, to_read);

        if (n < 0)
        {
            perror("read");
            close(fd);
            return 1;
        }

        if (n == 0)
            break; // EOF

        ssize_t written = 0;
        while (written < n)
        {
            ssize_t w = write(fd, buf + written, n - written);
            if (w < 0)
            {
                perror("write");
                close(fd);
                return 1;
            }
            written += w;
        }

        total += n;

        if (n != 0x1000)
            break;
    }
    fchmod(fd, 0500);
    close(fd);
    strcpy(path_out, path);
    return 0;
}

int main(int argc, char **argv)
{
    init();
    char path[0x50] = {0};
    if (get_file(path) != 0)
    {
        exit(1);
    }
    int listener = 0;
    pid_t pid = fork();

    if (pid == 0)
    {
        struct sock_filter filter[] = {
            BPF_STMT(BPF_RET | BPF_K, SECCOMP_RET_USER_NOTIF),
        };

        struct sock_fprog prog = {
            .len = sizeof(filter) / sizeof(filter[0]),
            .filter = filter,
        };

        prctl(PR_SET_NO_NEW_PRIVS, 1, 0, 0, 0);

        listener = seccomp(SECCOMP_SET_MODE_FILTER,
                           SECCOMP_FILTER_FLAG_NEW_LISTENER,
                           &prog);

        if (listener < 0)
        {
            perror("seccomp");
            return 1;
        }

        // We immediately try to close, it will halt here until the supervisor steals the listener fd and handles the close syscall
        close(listener);

        execve(path, NULL, NULL);
        perror("execve");
        _exit(1);
    }

    while (listener == 0)
    {
        usleep(10);
        vm_read(pid, &listener, sizeof(listener), &listener);
    }

    int pidfd = pidfd_open(pid, 0);
    // Steal the seccomp listener fd.
    listener = pidfd_getfd(pidfd, listener, 0);

    init_sup();
    supervisor(listener, pid, pidfd);
    exit(0);
}
