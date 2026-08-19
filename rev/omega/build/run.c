/* run.c - per-connection jail entrypoint for the PRX job executor. */
#include <errno.h>
#include <fcntl.h>
#include <signal.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#include <sys/wait.h>
#include <unistd.h>

#define APP_DIR "/app"
#define EXECUTOR_DEFAULT APP_DIR "/executor"
#define TMPL "/tmp/jobXXXXXX.prx"

#define MAX_B64 (8 * 1024) /* cap the submission line at 8 KiB of base64 */
#define PRX_HDR_SIZE 0x30u

static void put(const char *msg) {
    size_t n = strlen(msg);
    while (n) {
        ssize_t w = write(STDOUT_FILENO, msg, n);
        if (w <= 0)
            return; /* peer is gone; the caller's exit path handles it */
        msg += w;
        n -= (size_t)w;
    }
}

/* Read a single '\n'-terminated line from stdin without over-reading. */
static size_t read_line(char *buf, size_t maxlen) {
    size_t n = 0;
    while (n < maxlen) {
        char ch;
        ssize_t r = read(STDIN_FILENO, &ch, 1);
        if (r < 0 && errno == EINTR)
            continue;
        if (r <= 0) /* EOF or error before newline */
            break;
        if (ch == '\n')
            break;
        if (ch != '\r') /* tolerate CRLF clients */
            buf[n++] = ch;
    }
    return n;
}

static int b64val(unsigned char ch) {
    if (ch >= 'A' && ch <= 'Z')
        return ch - 'A';
    if (ch >= 'a' && ch <= 'z')
        return ch - 'a' + 26;
    if (ch >= '0' && ch <= '9')
        return ch - '0' + 52;
    if (ch == '+')
        return 62;
    if (ch == '/')
        return 63;
    return -1;
}

static long b64decode(const char *in, size_t len, uint8_t *out) {
    if (len % 4 != 0)
        return -1;
    if (len == 0)
        return 0;

    size_t pad = 0;
    if (in[len - 1] == '=')
        pad = (in[len - 2] == '=') ? 2 : 1;

    size_t nsym = len - pad;
    uint32_t acc = 0;
    size_t bits = 0;
    long n = 0;
    for (size_t i = 0; i < nsym; i++) {
        int v = b64val((unsigned char)in[i]);
        if (v < 0)
            return -1;
        acc = (acc << 6) | (uint32_t)v;
        bits += 6;
        if (bits >= 8) {
            bits -= 8;
            out[n++] = (uint8_t)(acc >> bits);
        }
    }
    return n;
}

static int write_all(int fd, const uint8_t *buf, size_t n) {
    while (n) {
        ssize_t w = write(fd, buf, n);
        if (w < 0 && errno == EINTR)
            continue;
        if (w <= 0)
            return -1;
        buf += w;
        n -= (size_t)w;
    }
    return 0;
}

int main(void) {
    /* The peer can vanish mid-write; report it through errno */
    signal(SIGPIPE, SIG_IGN);

    put("== PRX job executor ==\n");
    put("submit your PRX job as one line of base64:\n");

    static char line[MAX_B64];
    size_t len = read_line(line, sizeof line);

    static uint8_t blob[MAX_B64 / 4 * 3];
    long blen = b64decode(line, len, blob);
    if (blen < 0) {
        put("[-] invalid base64\n");
        return 1;
    }
    if (blen < (long)PRX_HDR_SIZE) {
        put("[-] too small to be a PRX\n");
        return 1;
    }

    char path[] = TMPL;
    int fd = mkstemps(path, 4); /* keep the ".prx" suffix */
    if (fd < 0) {
        put("[-] could not stage the job\n");
        return 1;
    }
    if (write_all(fd, blob, (size_t)blen) != 0) {
        close(fd);
        unlink(path);
        put("[-] could not stage the job\n");
        return 1;
    }
    close(fd);

    const char *executor = getenv("EXECUTOR");
    if (!executor || !*executor)
        executor = EXECUTOR_DEFAULT;

    /* The executor resolves "./.env" and the job resolves "./flag.txt". */
    if (chdir(APP_DIR) != 0) {
        unlink(path);
        put("[-] could not enter the app directory\n");
        return 1;
    }

    /* Fork rather than exec so the temp file still gets unlinked: /tmp is a
     * per-connection tmpfs sized by JAIL_TMP_SIZE, and leaking into a shared
     * one would let repeat submissions fill it. */
    pid_t pid = fork();
    if (pid < 0) {
        unlink(path);
        put("[-] could not spawn the executor\n");
        return 1;
    }
    if (pid == 0) {
        /* The job inherits this connection's stdin/stdout. */
        execl(executor, executor, path, (char *)NULL);
        _exit(127);
    }

    int status;
    while (waitpid(pid, &status, 0) < 0) {
        if (errno != EINTR)
            break;
    }
    unlink(path);

    if (WIFEXITED(status))
        return WEXITSTATUS(status);
    return 1;
}
