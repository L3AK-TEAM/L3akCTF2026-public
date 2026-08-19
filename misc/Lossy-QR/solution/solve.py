from pwn import *

io = remote('localhost', 10018)
#io = remote('<instance>.instances.ctf.l3ak.team', 1337, ssl=True)
data = open('solve.txt', 'rb').read()
io.sendlineafter(b'> ', data)
io.interactive()
