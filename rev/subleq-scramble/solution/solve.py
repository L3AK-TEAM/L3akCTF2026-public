import sys
import struct
from itertools import batched

# read file
if len(sys.argv) < 2:
    print("Provide path to data.subleq as argument.")
    exit()

fname = sys.argv[1]
with open(fname, "rb") as f:
    data = f.read()
mem = list(struct.unpack(f"<{len(data) // 2}h", data))
# analyze mem
timer_addr = mem.index(-9999)
tick_addr = timer_addr + 3
mem_addr = tick_addr + 4
w = 84
h = 38

dx_addr = tick_addr - 5
dy_addr = tick_addr - 4
x_addr = tick_addr - 2
y_addr = tick_addr - 1

# invert the ant to make the simulation reverse itself
mem[dx_addr] *= -1
mem[dy_addr] *= -1
mem[x_addr] -= mem[dx_addr]
mem[y_addr] -= mem[dy_addr]


def print_memory():
    for i, line in enumerate(batched(mem[:mem_addr], 3)):
        print(i * 3, line)


def print_grid():
    for row in batched(mem[mem_addr:], w):
        print("".join("[]" if tile else ". " for tile in row))


print_memory()


pc = 0
while mem[tick_addr] >= 0 and pc >= 0:
    a, b, c = mem[pc : pc + 3]

    # # print current instruction
    # print(pc, a, b, c)

    # # visualize grid every simulation step
    # if b == tick_addr:
    #     print_grid()
    #     input()

    if b < 0:
        n = mem[a]
        try:
            ch = chr(n)
        except:
            ch = "???"
        print(f"{n} ({ch})")
        pc = c
    else:
        mem[b] -= mem[a]
        if mem[b] <= 0:
            pc = c
        else:
            pc += 3

print_memory()
print_grid()
print(pc)
