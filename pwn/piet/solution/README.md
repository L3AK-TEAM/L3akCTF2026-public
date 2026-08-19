# Piet
### Author: kyc

The binary is an implementation of Piet, an esoteric programming language.
See https://www.dangermouse.net/esoteric/piet.html for a summary.

Here is the stack memory layout at interpret_program. Each row is 4 u32s:
```
           #################################################################################
rbp-0x430  # &stack                                # stack_depth       # CC                # -+
           #################################################################################  |
rbp-0x420  # DP                # row               # col               # 0                 #  |
           #################################################################################  |
rbp-0x410  # stack[0]          # stack[1]          # stack[2]          # stack[3]          #  |
           #################################################################################  |
rbp-0x400  # stack[4]          # stack[5]          # stack[6]          # stack[7]          #  |
           #################################################################################  |  interpret_program stack frame
           ...                                                                                |
           #################################################################################  |
rbp-0x20   # stack[252]        # stack[253]        # stack[254]        # stack[255]        #  |
           #################################################################################  |
rbp-0x10   # 0                                     # canary                                #  |
           #################################################################################  |
rbp        # prev rbp                              # return to main                        # -+
           #################################################################################
rbp+0x10   # img height        #  img width        #                                       # -+
           #################################################################################  |  main stack frame
rbp+0x20   #                                       # return to libc                        # -+
           #################################################################################
```
But there are no bounds checks when calling op_up and op_down, and we can do ROP. We're going to
use a ROP chain of only libc addresses:

    (ret; gadget) (pop rdi; ret; gadget) (/bin/sh) (system)

Since we're going to need a libc address, we'll first call op_up until the top of the stack is
right after the first libc address, which is the return address from main to libc:
```
           #################################################################################
rbp-0x20   # stack[252]        # stack[253]        # stack[254]        # stack[255]        #
           #################################################################################
rbp-0x10   # stack[256]                            # stack[258]  (canary)                  #
           #################################################################################
rbp        # stack[260]  (prev rbp)                # stack[262]  (return to main)          #
           #################################################################################
rbp+0x10   # stack[264]                            # stack[266]                            #
           #################################################################################
rbp+0x20   # stack[268]                            # stack[270]  (return to libc)          #  <- current top of stack
           #################################################################################
```
So we call op_up 272 times, and (return to libc) is on top of the Piet stack.

If the Piet stack used u64 values, then we could do this to push (ret; gadget) onto the Piet stack:

    op_dup                                       # duplicates (return to libc)
    op_push( (return to libc) - (ret; gadget) )
    op_sub

However, the Piet stack uses u32 values, which makes this more tricky. Our solver implements a
primitive dup_u64(diff), which reads the top two u32 values of the Piet stack as the u64 value V,
and pushes the u64 value V+diff as two u32 values onto the Piet stack. Using this primitive, we
can push the full ROP chain onto the stack:
```
           #################################################################################
rbp        # stack[260]  (prev rbp)                # stack[262]  (return to main)          #
           #################################################################################
rbp+0x10   # stack[264]                            # stack[266]                            #
           #################################################################################
rbp+0x20   # stack[268]                            # stack[270]  (return to libc)          #
           #################################################################################
rbp+0x30   # stack[272]  (ret; gadget)             # stack[274]  (pop rdi; ret; gadget)    #
           #################################################################################
rbp+0x40   # stack[276]  (/bin/sh)                 # stack[278]  (system)                  #  <- current top of stack
           #################################################################################
```
And finally, we use op_roll(18, 8) to move the ROP chain to the desired place, where it replaces the
return address of interpret_program back to main:
```
           #################################################################################
rbp        # stack[260]  (prev rbp)                # stack[262]  (ret; gadget)             #  <- overwritten return address
           #################################################################################
rbp+0x10   # stack[264]  (pop rdi; ret; gadget)    # stack[266]  (/bin/sh)                 #
           #################################################################################
rbp+0x20   # stack[268]  (system)                  # stack[270]  (return to main)          #
           #################################################################################
rbp+0x30   # stack[272]                            # stack[274]                            #
           #################################################################################
rbp+0x40   # stack[276]                            # stack[278]  (return to libc)          #  <- current top of stack
           #################################################################################
```
Flag: `L3AK{iVBORw0KGgoAAAANSUhEUgAAAAcAAAAHCAIAAABLMMCEAAAATElEQVR4nCWNwQ0AMQzCHKl7caPDZJya8kIBk6mLElBYKWLudRVtKgjYdc0aoLbbcUvQ47NNbfgqF+mt2z0Rdeebt147cB7Xnb5+n/4D5Dt5Fv+hKgAAAABJRU5ErkJggg}`
