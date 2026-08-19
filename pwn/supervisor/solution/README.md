# Supervisor Solution
### Author: White

The child has PR_SET_NO_NEW_PRIVS set so it is clear that the code execution in the child will not help getting the flag.
So the solution has to be about a bug in how the supervisor handles the syscalls.

The intended bug is in the dup2 syscall. If the old fd and new fd is the same, a fd will be created that is a dup for itself.
This essentially causes that bugged fd to point to fileid with the same id as the fd, which allows decrementing the refcnt of that file.
Using this we can use after free a page of mmaped memory.

This primitive can be used to overwrite the size of the fds array that has been mmaped by malloc to perform house of muney.
Increasing the size of the chunk then reallocing it causes some read only memory of the libc to be unmapped.
After which we can map on those pages and modify the data to point one of the functions into one gadget.
Thus we get code execution inside the parent which doesnt have PR_SET_NO_NEW_PRIVS set and can read the flag.

Flag: `L3AK{wow_this_supervisor_is_really_terrible}`
