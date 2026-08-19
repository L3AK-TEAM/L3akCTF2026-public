#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <stdbool.h>

void win() {
    FILE *f = fopen("flag.txt", "r");
    if (!f) {
        printf("Could not open flag.txt\n");
        exit(1);
    }
    char flag[0x60];
    fgets(flag, sizeof(flag), f);
    fclose(f);
    printf("%s\n", flag);
    exit(0);
}

void multiply_digit(int digit, uint32_t *product_bignum, int *product_bignum_len) {
    uint64_t carry = 0;
    for (int i = 0; i < *product_bignum_len; i++) {
        uint64_t prod = (uint64_t)product_bignum[i] * digit + carry;
        product_bignum[i] = (uint32_t)(prod & 0xFFFFFFFF);
        carry = prod >> 32;
    }
    if (carry) {
        product_bignum[*product_bignum_len] = (uint32_t)carry;
        (*product_bignum_len)++;
    }
}

void to_base_10(uint32_t *product_bignum, int product_bignum_len, char *out) {
    uint32_t tmp[0x1000];
    memcpy(tmp, product_bignum, product_bignum_len * sizeof(uint32_t));
    int tmp_size = product_bignum_len;

    char buf[0x1000];
    int pos = 0;

    while (tmp_size > 0) {
        uint64_t remainder = 0;
        for (int i = tmp_size - 1; i >= 0; i--) {
            uint64_t cur = (remainder << 32) | tmp[i];
            tmp[i] = (uint32_t)(cur / 10);
            remainder = cur % 10;
        }
        buf[pos++] = '0' + (int)remainder;

        while (tmp_size > 0 && tmp[tmp_size - 1] == 0)
            tmp_size--;
    }

    for (int i = 0; i < pos; i++)
        out[i] = buf[pos - 1 - i];
    out[pos] = '\0';
}

void run() {
    struct {
        char buf[0x1000];
        int product_bignum_len;
        uint32_t product_bignum[0x60];
    } s;

    printf("********************\n");
    printf("* BASIC CALCULATOR *\n");
    printf("********************\n");

    while (true) {
        s.product_bignum_len = 1;
        s.product_bignum[0] = 1;

        printf("Enter an expression> ");
        scanf("%s", s.buf);

        if (strcmp(s.buf, "quit") == 0)
            break;

        for (int i = 0; ; i++) {
            if (i % 2 == 0) {
                if (s.buf[i] >= '0' && s.buf[i] <= '9') {
                    multiply_digit(s.buf[i] - '0', s.product_bignum, &s.product_bignum_len);
                } else if (s.buf[i] >= 'a' && s.buf[i] <= 'f') {
                    multiply_digit(s.buf[i] - 'a' + 10, s.product_bignum, &s.product_bignum_len);
                } else if (s.buf[i] >= 'A' && s.buf[i] <= 'F') {
                    multiply_digit(s.buf[i] - 'A' + 10, s.product_bignum, &s.product_bignum_len);
                } else if (s.buf[i] == '-') {
                    printf("Sorry, negative numbers are not supported for now\n");
                    exit(1);
                } else {
                    printf("Expected digit\n");
                    exit(1);
                }
            } else {
                if (s.buf[i] == '\0') {
                    break;
                } else if (s.buf[i] >= '0' && s.buf[i] <= '9') {
                    printf("Sorry, only single-digit numbers are supported for now\n");
                    exit(1);
                } else if (s.buf[i] >= 'a' && s.buf[i] <= 'f') {
                    printf("Sorry, only single-digit numbers are supported for now\n");
                    exit(1);
                } else if (s.buf[i] >= 'A' && s.buf[i] <= 'F') {
                    printf("Sorry, only single-digit numbers are supported for now\n");
                    exit(1);
                } else if (s.buf[i] == '+' || s.buf[i] == '-' || s.buf[i] == '/') {
                    printf("Sorry, only multiplication is supported for now\n");
                    exit(1);
                } else if (s.buf[i] == '.') {
                    printf("Sorry, only integers are supported for now\n");
                    exit(1);
                } else if (s.buf[i] != '*' && s.buf[i] != 'x') {
                    printf("Unexpected character\n");
                    exit(1);
                }
            }
        }

        to_base_10(s.product_bignum, s.product_bignum_len, s.buf);
        printf("Result: %s\n\n", s.buf);
    }
}

int main() {
    setbuf(stdin, NULL);
    setbuf(stdout, NULL);

    run();
}
