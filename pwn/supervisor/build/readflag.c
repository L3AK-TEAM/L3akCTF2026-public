#include <sys/types.h>
#include <sys/stat.h>
#include <fcntl.h>
#include <unistd.h>
#include <string.h>
#include <stdlib.h>

int main() {
    char buf[0x100] = {0};
    int fd = open("/flag.txt", O_RDONLY);
    read(fd, buf, 0x100);
    write(STDOUT_FILENO, buf, strlen(buf));
    exit(0);
}