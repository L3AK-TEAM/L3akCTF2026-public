from Crypto.Util.number import getPrime, isPrime
from math import gcd
from secrets import randbelow

N = 9 ** 99

# generate 99 functions of the form f_i(s) = a_i * s + b_i (mod 9^99)
print('Here are my functions:')
functions = []
while len(functions) < 99:
    a = randbelow(N)
    b = randbelow(N)
    if gcd(a, 9) == 1:
        print(f'f_{len(functions)}(s) = {a} * s + {b}')
        functions.append((a, b))
print()

composed_a, composed_b = 1, 0

for _ in range(999):
    print('Menu')
    print('1. Compose functions')
    print('2. Get challenge')
    print('3. Exit')
    choice = int(input('Enter choice >'))

    if choice == 1:
        print('Enter function indices:')
        for _ in range(9999):
            line = input().strip()
            if line == 'done':
                break
            else:
                a, b = functions[int(line)]
                composed_a, composed_b = (composed_a * a) % N, (composed_b * a + b) % N

    elif choice == 2:
        print('Generating factors...')
        secret = getPrime(N.bit_length() - 1)
        start = getPrime(N.bit_length() - 1)
        end = (start * composed_a + composed_b) % N
        print(f'Product: {secret * start * end if isPrime(end) else "REDACTED"}')

        guess = int(input('What was my secret? >'))
        if guess == secret:
            print(open('flag.txt').read())
            exit(0)

    elif choice == 3:
        print('Goodbye!')
        exit(0)

    else:
        print('Invalid choice')
        exit(-1)
