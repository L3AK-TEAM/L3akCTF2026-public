#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <sys/wait.h>

#define MAX_HEX 257

int main(void)
{
    char buf[MAX_HEX + 1];

    puts("Welcome to LattiaVM!");

    printf("Input hex-encoded bytecode (no more than 256 hex chars):\n");
    fflush(stdout);

    if (!fgets(buf, sizeof(buf), stdin))
        return 0;
    buf[strcspn(buf, "\n")] = '\0';

    pid_t pid = fork();
    if (pid == 0)
    {
        freopen("/dev/null", "r", stdin);
        char vm[] = "/app/lattia-vm";
        execl(vm, vm, buf, NULL);
        perror("execl");
        _exit(1);
    }
    waitpid(pid, NULL, 0);

    return 0;
}