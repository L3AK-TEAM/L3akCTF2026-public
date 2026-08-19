from pwn import *
from sage.all import *
from sage.modules.free_module_integer import IntegerLattice
from tqdm import tqdm, trange
import random

start = time.time()

N = 9**99
R = Zmod(N)

io = remote('localhost', 10027)

functions = []
for _ in range(99):
    res = io.recvregex(b'.* = (\\d+) \\* s \\+ (\\d+)\n', capture=True)
    a = R(int(res.group(1)))
    b = R(int(res.group(2)))
    functions.append((a, b))

# compute discrete log mod 9^99
# group is Z_2 x Z_{N/3}
def discrete_log_modN(a):
    if a % 3 == 2:
        return 1, discrete_log_modN(-a)[1]
    g = R(4)
    e = 0
    for i in range(197):
        which = [g**(3**(196-i) * (e + j * 3**i)) for j in range(3)].index(a**(3**(196-i)))
        e += which * 3**i
    assert g**e == a
    return 0, e

# finds linear combination of "vectors" such that they sum to "target_vector" (in the given mods)
# bias: the approximate average of the coefficients in the linear combinations
def find_linear_combination(vectors, target_vector, mods, bias=27):
    W = 99**99  # big weight
    n = len(vectors) + len(target_vector)
    M = [[0] * n for _ in range(n)]
    for i, v in enumerate(vectors):
        M[i][i] = 1
        for j, target in enumerate(target_vector):
            M[i][len(vectors) + j] = v[j] * W
    for j in range(len(target_vector)):
        M[len(vectors) + j][len(vectors) + j] = mods[j] * W
    v = IntegerLattice(M).approximate_closest_vector([bias] * len(vectors) + [t * W for t in target_vector])
    return [int(n) for n in v[:len(vectors)]]

def compose_functions(functions, indices):
    composed_a, composed_b = R(1), R(0)
    for index in indices:
        a, b = functions[index]
        composed_a, composed_b = (composed_a * a), (composed_b * a + b)
    return composed_a, composed_b

vectors = [discrete_log_modN(a) for a, _ in functions[:80]]

# find functions that compose to f(s) = 2s + [constant]
target_vector = discrete_log_modN(R(2))
a2_counts = find_linear_combination(vectors, target_vector, [2, N//3])
a2_indices = [i for i, count in enumerate(a2_counts) for j in range(count)]
a2_a, a2_b = compose_functions(functions, a2_indices)
assert a2_a == 2

# find functions that compose to f(s) = s + [constant]
# find 80 of them
target_vector = discrete_log_modN(R(1))
a1_counts = find_linear_combination(vectors, target_vector, [2, N//3])
a1_indices = [i for i, count in enumerate(a1_counts) for j in range(count)]
all_a1_indices = []
all_a1_bs = []
for _ in range(80):
    random.shuffle(a1_indices)
    a1_a, a1_b = compose_functions(functions, a1_indices)
    assert a1_a == 1
    all_a1_indices.append(list(a1_indices))
    all_a1_bs.append(a1_b)

# now compose those into f(s) = 2s + 1
part_counts = find_linear_combination([[int(n)] for n in all_a1_bs], [1 - int(a2_b)], [N])
final_indices = list(a2_indices)
for i, count in enumerate(part_counts):
    final_indices.extend(all_a1_indices[i] * count)
final_a, final_b = compose_functions(functions, final_indices)
print('final', final_a, final_b)
assert final_a == 2
assert final_b == 1
print('num indices', len(final_indices))

# send indices to server
for batch in tqdm(group(9000, final_indices)):
    io.sendlineafter(b'Enter choice >', b'1')
    io.recvuntil(b'Enter function indices:')
    payload = b''
    for index in batch:
        payload += str(index).encode() + b'\n'
    io.send(payload)
    io.sendline(b'done')
print(time.time() - start, 'Sent indices')

for _ in trange(400):
    io.sendlineafter(b'Enter choice >', b'2')

    io.recvuntil(b'Product: ')
    res = io.recvline().strip()
    if res == b'REDACTED':
        io.sendlineafter(b'What was my secret? >', b'0')
        continue
    n = int(res)
    print('product', n)

    g = gcd(pow(2, 2 * n, n) - 1, n)
    for p, _ in factor(g):
        if g > 999999999:
            print(time.time() - start, 'found', g)
            secret = n // p // ((p - 1) // 2)
            io.sendlineafter(b'What was my secret? >', str(secret).encode())
            io.interactive()
            exit()
    else:
        io.sendlineafter(b'What was my secret? >', b'0')
