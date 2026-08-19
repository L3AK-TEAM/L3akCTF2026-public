/* echo -- reads lines from stdin and echoes them to stdout. */
#include "syscall.h"
#include <stddef.h>

#define BUF_SIZE 512

#define STDIN 0
#define STDOUT 1

#define RESET "\033[0m"
#define STY(style, text) style text RESET

#define LOGO                                                                   \
    "███████╗ ██████╗██╗  ██╗ ██████╗ \n"                                      \
    "██╔════╝██╔════╝██║  ██║██╔═══██╗\n"                                      \
    "█████╗  ██║     ███████║██║   ██║\n"                                      \
    "██╔══╝  ██║     ██╔══██║██║   ██║\n"                                      \
    "███████╗╚██████╗██║  ██║╚██████╔╝\n"                                      \
    "╚══════╝ ╚═════╝╚═╝  ╚═╝ ╚═════╝ \n"

#define AZURE "\033[38;5;39m"
#define DENIM "\033[38;5;67m"
#define SAGE "\033[38;5;114m"
#define BOLD "\033[1m"
#define DIM "\033[2m"

#define CLEAR_LN "\r\033[K"

static size_t _strlen(const char *s) {
    const char *p = s;
    while (*s)
        ++s;
    return s - p;
}

static int _strcmp(const char *l, const char *r) {
    while (*l == *r && *l)
        ++l, ++r;

    return *(unsigned char *)l - *(unsigned char *)r;
}

static long _puts(const char *s) {
    return _syscall(SYS_write, STDOUT, (long)(void *)s, _strlen(s));
}

static void send_banner(void) {
    // clang-format off
    _puts("\033[2J\033[H"); /* clear screen, cursor home */
    _puts(
        STY(AZURE, LOGO)
        STY(BOLD AZURE, "       echo ") STY(DIM, "server · v1.0") "\n"
        STY(DENIM, "─────────────────────────────────") "\n"
        STY(DIM, "•  ") "type a message, press " STY(SAGE, "↵") " to echo it\n"
        STY(DIM, "•  ") STY(SAGE, "/quit") " to disconnect\n"\
    );
    // clang-format on
}

static void echo(void) {
    send_banner();
    _puts(STY(AZURE, "  > "));

    char buf[BUF_SIZE];
    char line[BUF_SIZE];
    size_t len = 0;

    for (long n;
         (n = _syscall(SYS_read, STDIN, (long)(void *)buf, sizeof buf)) > 0;) {
        for (long i = 0; i < n; i++) {
            if (buf[i] != '\n') {
                if (len < sizeof line - 1)
                    line[len++] = buf[i];
                continue;
            }

            if (len > 0 && line[len - 1] == '\r') /* support CRLF clients */
                len--;
            line[len] = '\0';

            if (_strcmp(line, "/quit") == 0)
                goto done;

            // Echo line
            _puts(CLEAR_LN STY(DIM, "  ↩  ") BOLD AZURE);
            _puts(line);
            _puts(RESET "\n");

            _puts(STY(AZURE, "  > "));
            len = 0;
        }
    }

done:
    _puts(STY(DIM, "  goodbye.\n"));
}

void _exit(int code) {
    _syscall(SYS_exit, code);
}

void _start(void) {
    echo();
    _exit(0);
}
