#include <errno.h>
#include <fcntl.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/wait.h>
#include <unistd.h>

#include "prismvm.h"
#include "verifier_prx.h" /* generated: verifier_prx[], verifier_prx_len */

#define PRX_HDR_SIZE 0x30u
#define PRX_MAC_OFF 0x10u
#define MAC_SIZE 32u

static long read_file(const char *path, uint8_t **out) {
    FILE *f = fopen(path, "rb");
    if (!f) {
        fprintf(stderr, "executor: open %s: %s\n", path, strerror(errno));
        return -1;
    }
    fseek(f, 0, SEEK_END);
    long sz = ftell(f);
    fseek(f, 0, SEEK_SET);
    uint8_t *buf = malloc(sz > 0 ? (size_t)sz : 1);
    if (!buf || (sz > 0 && fread(buf, 1, (size_t)sz, f) != (size_t)sz)) {
        fprintf(stderr, "executor: read %s failed\n", path);
        fclose(f);
        free(buf);
        return -1;
    }
    fclose(f);
    *out = buf;
    return sz;
}

static int hexval(int ch) {
    if (ch >= '0' && ch <= '9')
        return ch - '0';
    if (ch >= 'a' && ch <= 'f')
        return ch - 'a' + 10;
    if (ch >= 'A' && ch <= 'F')
        return ch - 'A' + 10;
    return -1;
}

static long decode_secret(const char *val, uint8_t **out) {
    while (*val == ' ' || *val == '\t')
        val++;

    size_t hexlen = strspn(val, "0123456789abcdefABCDEF");
    if (hexlen == 0 || hexlen % 2 != 0) {
        fprintf(stderr, "executor: SECRET must be an even-length hex string\n");
        return -1;
    }
    uint8_t *secret = malloc(hexlen / 2);
    for (size_t i = 0; i < hexlen / 2; i++)
        secret[i] =
            (uint8_t)((hexval(val[2 * i]) << 4) | hexval(val[2 * i + 1]));
    *out = secret;
    return (long)(hexlen / 2);
}

static long load_secret(const char *path, uint8_t **out) {
    uint8_t *raw;
    long n = read_file(path, &raw);
    if (n < 0)
        return -1;

    const char *key = "SECRET=";
    size_t keylen = strlen(key);
    char *text = (char *)raw;
    char *val = NULL;
    for (char *line = strtok(text, "\r\n"); line; line = strtok(NULL, "\r\n")) {
        while (*line == ' ' || *line == '\t')
            line++;
        if (*line == '#')
            continue;
        if (strncmp(line, key, keylen) == 0) {
            val = line + keylen;
            break;
        }
    }
    if (!val) {
        fprintf(stderr, "executor: no SECRET= in %s\n", path);
        free(raw);
        return -1;
    }

    long slen = decode_secret(val, out);
    free(raw);
    return slen;
}

static int write_all(int fd, const void *buf, size_t n) {
    const uint8_t *p = buf;
    while (n) {
        ssize_t w = write(fd, p, n);
        if (w <= 0)
            return -1;
        p += w;
        n -= (size_t)w;
    }
    return 0;
}

static void put_u32le(uint8_t b[4], uint32_t v) {
    b[0] = (uint8_t)v;
    b[1] = (uint8_t)(v >> 8);
    b[2] = (uint8_t)(v >> 16);
    b[3] = (uint8_t)(v >> 24);
}

static int run_prx_mem(const uint8_t *img, size_t len) {
    CPU c;
    cpu_init(&c);
    if (load_prx_mem(&c, img, len) != 0) {
        mmu_deinit(&c.mmu);
        return -1;
    }
    setup_stack(&c);
    cpu_run(&c);
    int code = c.exit_code;
    mmu_deinit(&c.mmu);
    return code;
}

static int run_verifier(const uint8_t *secret, uint32_t slen,
                        const uint8_t *msg, uint32_t mlen, const uint8_t *tag) {
    int pipefd[2];
    if (pipe(pipefd) != 0) {
        perror("pipe");
        return -1;
    }

    pid_t pid = fork();
    if (pid < 0) {
        perror("fork");
        close(pipefd[0]);
        close(pipefd[1]);
        return -1;
    }
    if (pid == 0) {
        dup2(pipefd[0], STDIN_FILENO);
        close(pipefd[0]);
        close(pipefd[1]);
        int code = run_prx_mem(verifier_prx, verifier_prx_len);
        _exit(code & 0xff);
    }

    close(pipefd[0]);
    uint8_t hdr[4];
    int ok = 0;
    put_u32le(hdr, slen);
    ok |= write_all(pipefd[1], hdr, 4);
    ok |= write_all(pipefd[1], secret, slen);
    put_u32le(hdr, mlen);
    ok |= write_all(pipefd[1], hdr, 4);
    ok |= write_all(pipefd[1], msg, mlen);
    ok |= write_all(pipefd[1], tag, MAC_SIZE);
    close(pipefd[1]);

    int status;
    if (waitpid(pid, &status, 0) < 0) {
        perror("waitpid");
        return -1;
    }
    if (ok != 0)
        return -1;
    if (!WIFEXITED(status))
        return -1;
    return WEXITSTATUS(status);
}

int main(int argc, char **argv) {
    if (argc != 2) {
        fprintf(stderr, "usage: %s <job.prx>\n", argv[0]);
        return 2;
    }
    const char *job = argv[1];

    /* Secret precedence: the SECRET env var (hex) if set, else the SECRET=<hex>
     * line in ./.env. */
    uint8_t *secret;
    long slen;
    const char *secret_hex = getenv("SECRET");
    if (secret_hex && *secret_hex) {
        slen = decode_secret(secret_hex, &secret);
    } else {
        slen = load_secret(".env", &secret);
    }
    if (slen < 0)
        return 1;

    uint8_t *jobbuf;
    long jsz = read_file(job, &jobbuf);
    if (jsz < 0) {
        free(secret);
        return 1;
    }
    if (jsz < (long)PRX_HDR_SIZE) {
        fprintf(stderr, "executor: %s too small to be a PRX\n", job);
        free(secret);
        free(jobbuf);
        return 1;
    }

    const uint8_t *tag = jobbuf + PRX_MAC_OFF;
    const uint8_t *msg = jobbuf + PRX_HDR_SIZE;
    uint32_t mlen = (uint32_t)(jsz - (long)PRX_HDR_SIZE);

    int vexit = run_verifier(secret, (uint32_t)slen, msg, mlen, tag);
    free(secret);

    if (vexit != 0) {
        fprintf(stderr, "[-] Verification failed\n");
        free(jobbuf);
        return 1;
    }
    fprintf(stderr, "[+] Verified\n");

    /* Run the job in the in-process VM. It inherits the runner's stdio. */
    int rc = run_prx_mem(jobbuf, (size_t)jsz);
    free(jobbuf);
    return rc < 0 ? 1 : rc;
}
