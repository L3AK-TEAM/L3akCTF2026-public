#include <fcntl.h>
#include <unistd.h>

int main(void) {
    char buffer[4096];
    ssize_t count;
    int fd = open("/flag.txt", O_RDONLY);

    if (fd < 0)
        return 1;
    while ((count = read(fd, buffer, sizeof(buffer))) > 0)
        if (write(STDOUT_FILENO, buffer, (size_t)count) != count)
            return 1;
    close(fd);
    return count < 0;
}
