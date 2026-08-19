#include "whatwho.h"

#include <errno.h>
#include <inttypes.h>
#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <unistd.h>

static bool parse_nonce(const char *text, uint64_t *out) {
    if (text == NULL || strlen(text) != 16u) {
        return false;
    }
    uint64_t value = 0;
    for (size_t i = 0; i < 16u; ++i) {
        unsigned digit;
        if (text[i] >= '0' && text[i] <= '9') {
            digit = (unsigned)(text[i] - '0');
        } else if (text[i] >= 'a' && text[i] <= 'f') {
            digit = (unsigned)(text[i] - 'a' + 10);
        } else if (text[i] >= 'A' && text[i] <= 'F') {
            digit = (unsigned)(text[i] - 'A' + 10);
        } else {
            return false;
        }
        value = (value << 4) | digit;
    }
    *out = value;
    return true;
}

static uint64_t fallback_nonce(void) {
    uint64_t value = (uint64_t)time(NULL);
    value ^= (uint64_t)getpid() << 32;
    value ^= (uintptr_t)&value;
    value ^= value >> 27;
    value *= UINT64_C(0x3C79AC492BA7B653);
    value ^= value >> 33;
    value *= UINT64_C(0x1C69B3F74AC4AE35);
    value ^= value >> 27;
    return value;
}

static uint64_t session_nonce(void) {
    const char *fixed = getenv("WHATWHO_NONCE");
    uint64_t value;
    if (fixed != NULL) {
        if (!parse_nonce(fixed, &value)) {
            fprintf(stderr, "WHATWHO_NONCE must contain 16 hexadecimal digits\n");
            exit(2);
        }
        return value;
    }

    int random_fd = open("/dev/urandom", O_RDONLY);
    ssize_t received = -1;
    if (random_fd >= 0) {
        received = read(random_fd, &value, sizeof(value));
        close(random_fd);
    }
    if (received != (ssize_t)sizeof(value)) {
        value = fallback_nonce();
    }
    return value;
}

int main(int argc, char **argv) {
    setvbuf(stdin, NULL, _IONBF, 0);
    setvbuf(stdout, NULL, _IONBF, 0);
    setvbuf(stderr, NULL, _IONBF, 0);

    if (argc != 2) {
        fprintf(stderr, "usage: %s vault.wwc\n", argv[0]);
        return 2;
    }

    ww_cartridge cartridge;
    if (!ww_load_cartridge(argv[1], &cartridge)) {
        return 2;
    }

    uint64_t nonce = session_nonce();
    const char *flag = getenv("WHATWHO_FLAG");
    if (flag == NULL || flag[0] == '\0') {
        flag = "LOCAL_INSTANCE_HAS_NO_EVENT_FLAG";
    }

    puts("┌────────────────────────────────────────────────────────┐");
    puts("│                      WHAT / WHO                        │");
    puts("└────────────────────────────────────────────────────────┘");
    printf("Instance seed: %016" PRIx64 "\n", nonce);
    puts("Answers are exact and case-sensitive.\n");

    bool success = ww_run(&cartridge, nonce, flag);
    ww_free_cartridge(&cartridge);
    return success ? 0 : 1;
}
