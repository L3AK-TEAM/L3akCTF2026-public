# Hardware is a scam Solution
### Author: JAGIC

If you understand circuits, this challenge should make sense, but the solve path still may seem unclear.

The key idea behind this challenge was to simplify the circuit. There are a lot of sections throughout the circuit that can be simplified to much shorter logic gates, and thus brute forcers will be much faster / not necessary.

First, let's look at the top block. There are a lot of logic gates on inputs C1-C4. Let's first see how many possible solutions C1-C4 have with just these logic gates.

We see that there are 5 circuits that all need to be correct for this circuit block to respond true. These logic gates are below:

```
((C1 * C4) + C1) xnor C2 == 5c
(C1 & C3) nor (C2 xor C4) == 87
C3 xor C4 == 0a
(C2 xor C1) xor C3 == 3e
C3 - C1 == 4f
```
With these 5 equations, we can brute force character by character to find all possibilities (in the same way used in `Software is a scam`). My solve script is attached at `solve1.py`.

We find that there exit only 2 possible combinations of C1-C4 that satisfy this circuit. `l3ak` and `L3AK`. We can note this down for our next script, as we can see that the rest of the circuit requires these characters to be known.

The next step is to map out all the logic gates in the second chunk. This part will most likely take you the longest. Patience is key here lol, you will get to the end eventually.

The below equations are all - circuits in the 2nd chunk:
```
(C5 xor C34) == 0x06

(C6 - (
    (C1 >> 5)
    *
    (((C15 | C24) / (C24 | C15))
    | (((C21 nand C30) / (C30 nand C21)) << 4))
)) == 0x20

(C7 - (
    (C3 >> 5)
    *
    (((C21 nor C30) / (C30 nor C21))
    | (((C14 xnor C23) / (C23 xnor C14)) << 6))
)) == 0xB2

(C8 - (
    (C4 >> 5)
    *
    (((((C27 xor C9) | C18) / (C18 | (C9 xor C27)))
    | ((((C19 & C28) | C10) / (C10 | (C28 & C19))) << 2))
    | ((((C31 + C13) | C22) / (C22 | (C13 + C31))) << 3))
)) == 0x49

(C9 + (
    (C1 >> 5)
    *
    (((((C32 | C14) / (C14 | C32)) << 3)
    | (((C17 nand C26) / (C26 nand C17)) << 4))
    | (((C29 nor C11) / (C11 nor C29)) << 5))
)) == 0xDB

(C10 - (
    (C3 >> 5)
    *
    (((((C29 xnor C11) / (C11 xnor C29)) << 1)
    | ((((C14 xor C23) | C32) / (C32 | (C23 xor C14))) << 2))
    | ((((C26 & C7) | C17) / (C17 | (C7 & C26))) << 3))
)) == 0x48

(C11 + (
    (C4 >> 5)
    *
    ((((((C33 + C15) | C24) / (C24 | (C15 + C33)))
    | (((C12 | C21) / (C21 | C12)) << 4))
    | (((C31 nand C13) / (C13 nand C31)) << 6))
    | (((C16 nor C25) / (C25 nor C16)) << 7))
)) == 0xD2

(C12 + (
    (C1 >> 5)
    *
    ((((((C29 xnor C10) / (C10 xnor C29)) << 1)
    | ((((C21 xor C30) | C11) / (C11 | (C30 xor C21))) << 3))
    | ((((C33 & C15) | C24) / (C24 | (C15 & C33))) << 4))
    | ((((C18 + C27) | C8) / (C8 | (C27 + C18))) << 5))
)) == 0xE3

(C13 xor (
    (C3 >> 5)
    *
    (((C10 | C20) / (C20 | C10))
    | (((C31 nand C12) / (C12 nand C31)) << 6))
)) == 0xF0

(C14 - (
    (C4 >> 5)
    *
    (((C31 nor C12) / (C12 nor C31)) << 2)
)) == 0x57

(C15 + (
    (C1 >> 5)
    *
    ((((C18 xnor C27) / (C27 xnor C18))
    | ((((C30 xor C11) | C21) / (C21 | (C11 xor C30))) << 1))
    | ((((C29 & C10) | C20) / (C20 | (C10 & C29))) << 4))
)) == 0x8E

(C16 - (
    (C3 >> 5)
    *
    ((((C29 + C10) | C20) / (C20 | (C10 + C29)))
    | (((C22 | C31) / (C31 | C22)) << 6))
)) == 0xAF

(C17 + (
    (C4 >> 5)
    *
    ((((C7 nand C16) / (C16 nand C7))
    | (((C13 nor C23) / (C23 nor C13)) << 4))
    | (((C26 xnor C7) / (C7 xnor C26)) << 5))
)) == 0xC6

(C18 + (
    (C1 >> 5)
    *
    ((((C19 xor C28) | C9) / (C9 | (C28 xor C19)))
    | ((((C10 & C20) | C29) / (C29 | (C20 & C10))) << 2))
)) == 0x6E

(C19 + (
    (C3 >> 5)
    *
    ((((((C25 + C6) | C15) / (C15 | (C6 + C25)))
    | (((C9 | C18) / (C18 | C9)) << 1))
    | (((C23 nand C32) / (C32 nand C23)) << 6))
    | (((C7 nor C16) / (C16 nor C7)) << 7))
)) == 0xB9

(C20 + (
    (C4 >> 5)
    *
    (((((C21 xnor C30) / (C30 xnor C21)) << 1)
    | ((((C12 xor C22) | C31) / (C31 | (C22 xor C12))) << 3))
    | ((((C25 & C6) | C15) / (C15 | (C6 & C25))) << 4))
)) == 0x82

(C21 - (
    (C1 >> 5)
    *
    (((((C11 + C20) | C30) / (C30 | (C20 + C11))) << 2)
    | (((C31 | C12) / (C12 | C31)) << 4))
)) == 0x37

(C22 - (
    (C3 >> 5)
    *
    ((((C10 nand C19) / (C19 nand C10)) << 1)
    | (((C30 nor C11) / (C11 nor C30)) << 3))
)) == 0x55

(C23 - (
    (C4 >> 5)
    *
    ((((C9 xnor C18) / (C18 xnor C9))
    | ((((C8 xor C17) | C27) / (C27 | (C17 xor C8))) << 3))
    | ((((C28 & C9) | C18) / (C18 | (C9 & C28))) << 5))
)) == 0xFC

(C24 - (
    (C1 >> 5)
    *
    ((((((C20 + C30) | C11) / (C11 | (C30 + C20)))
    | (((C27 | C8) / (C8 | C27)) << 4))
    | (((C18 nand C28) / (C28 nand C18)) << 6))
    | (((C31 nor C12) / (C12 nor C31)) << 7))
)) == 0xBD

(C25 - (
    (C3 >> 5)
    *
    (((((C16 xnor C26) / (C26 xnor C16)) << 1)
    | ((((C8 xor C17) | C27) / (C27 | (C17 xor C8))) << 3))
    | ((((C28 & C9) | C18) / (C18 | (C9 & C28))) << 5))
)) == 0xF4

(C26 - (
    (C4 >> 5)
    *
    ((((C21 + C31) | C12) / (C12 | (C31 + C21))) << 4)
)) == 0x14

(C27 + (
    (C1 >> 5)
    *
    ((((C21 | C31) / (C31 | C21))
    | (((C6 nand C15) / (C15 nand C6)) << 1))
    | (((C33 nor C14) / (C14 nor C33)) << 4))
)) == 0x98

(C28 xor (
    (C3 >> 5)
    *
    (((((C12 xnor C21) / (C21 xnor C12)) << 1)
    | ((((C24 xor C6) | C15) / (C15 | (C6 xor C24))) << 2))
    | ((((C9 & C18) | C27) / (C27 | (C18 & C9))) << 3))
)) == 0x58

(C29 + (
    (C4 >> 5)
    *
    ((((((C23 + C33) | C14) / (C14 | (C33 + C23))) << 1)
    | (((C8 | C17) / (C17 | C8)) << 2))
    | (((C14 nand C23) / (C23 nand C14)) << 6))
)) == 0x03

(C30 - (
    (C1 >> 5)
    *
    (((((C27 nor C9) / (C9 nor C27))
    | (((C12 xnor C21) / (C21 xnor C12)) << 1))
    | ((((C11 xor C20) | C29) / (C29 | (C20 xor C11))) << 4))
    | ((((C23 & C33) | C14) / (C14 | (C33 & C23))) << 5))
)) == 0xCE

(C31 + (
    (C3 >> 5)
    *
    (((((C23 + C33) | C14) / (C14 | (C33 + C23))) << 1)
    | (((C15 | C24) / (C24 | C15)) << 3))
)) == 0x66

(C32 xor (
    (C4 >> 5)
    *
    (((((C29 nand C11) / (C11 nand C29)) << 1)
    | (((C28 nor C10) / (C10 nor C28)) << 4))
    | (((C20 xnor C29) / (C29 xnor C20)) << 6))
)) == 0xC1

(C33 xor (
    (C1 >> 5)
    *
    (((((C13 xor C22) | C31) / (C31 | (C22 xor C13))) << 1)
    | ((((C25 & C7) | C16) / (C16 | (C7 & C25))) << 2))
)) == 0x2D

(C34 - (C1 xor C3)) == 0x70
```

Immediately, we see a whole bunch of contradictive statements. Things such as `(((C13 xor C22) | C31) / (C31 | (C22 xor C13)))` or `((C27 nor C9) / (C9 nor C27))` where you have the same communative function dividing itself. The key idea of this challenge was to simplify all of these communative functions to cut away useless functions. If you found this pattern earlier, you could have skipped a bunch of logic gates. After doing so, you get the following (much nicer) series of equations:

```
(C5 xor C34) == 0x06
(C6 - ((C1 >> 5) * (1 | (1 << 4)))) == 0x20
(C7 - ((C3 >> 5) * (1 | (1 << 6)))) == 0xB2
(C8 - ((C4 >> 5) * ((1 | (1 << 2)) | (1 << 3)))) == 0x49
(C9 + ((C1 >> 5) * (((1 << 3) | (1 << 4)) | (1 << 5)))) == 0xDB
(C10 - ((C3 >> 5) * (((1 << 1) | (1 << 2)) | (1 << 3)))) == 0x48
(C11 + ((C4 >> 5) * (((1 | (1 << 4)) | (1 << 6)) | (1 << 7)))) == 0xD2
(C12 + ((C1 >> 5) * ((((1 << 1) | (1 << 3)) | (1 << 4)) | (1 << 5)))) == 0xE3
(C13 xor ((C3 >> 5) * (1 | (1 << 6)))) == 0xF0
(C14 - ((C4 >> 5) * (1 << 2))) == 0x57
(C15 + ((C1 >> 5) * ((1 | (1 << 1)) | (1 << 4)))) == 0x8E
(C16 - ((C3 >> 5) * (1 | (1 << 6)))) == 0xAF
(C17 + ((C4 >> 5) * ((1 | (1 << 4)) | (1 << 5)))) == 0xC6
(C18 + ((C1 >> 5) * (1 | (1 << 2)))) == 0x6E
(C19 + ((C3 >> 5) * (((1 | (1 << 1)) | (1 << 6)) | (1 << 7)))) == 0xB9
(C20 + ((C4 >> 5) * (((1 << 1) | (1 << 3)) | (1 << 4)))) == 0x82
(C21 - ((C1 >> 5) * ((1 << 2) | (1 << 4)))) == 0x37
(C22 - ((C3 >> 5) * ((1 << 1) | (1 << 3)))) == 0x55
(C23 - ((C4 >> 5) * ((1 | (1 << 3)) | (1 << 5)))) == 0xFC
(C24 - ((C1 >> 5) * (((1 | (1 << 4)) | (1 << 6)) | (1 << 7)))) == 0xBD
(C25 - ((C3 >> 5) * (((1 << 1) | (1 << 3)) | (1 << 5)))) == 0xF4
(C26 - ((C4 >> 5) * (1 << 4))) == 0x14
(C27 + ((C1 >> 5) * ((1 | (1 << 1)) | (1 << 4)))) == 0x98
(C28 xor ((C3 >> 5) * (((1 << 1) | (1 << 2)) | (1 << 3)))) == 0x58
(C29 + ((C4 >> 5) * (((1 << 1) | (1 << 2)) | (1 << 6)))) == 0x03
(C30 - ((C1 >> 5) * (((1 | (1 << 1)) | (1 << 4)) | (1 << 5)))) == 0xCE
(C31 + ((C3 >> 5) * ((1 << 1) | (1 << 3)))) == 0x66
(C32 xor ((C4 >> 5) * (((1 << 1) | (1 << 4)) | (1 << 6)))) == 0xC1
(C33 xor ((C1 >> 5) * ((1 << 1) | (1 << 2)))) == 0x2D
(C34 - (C1 xor C3)) == 0x70
```

From here, since every equation has their own new variable (C1, C3, and C4 have been "found"), we can simply loop through every letter for every character index and get the flag. If you simplify further, you can do this without brute forcing, but since we've written out all of this logic in almost python syntax, its probably faster just to port these equations to python and solve. Remember that everything here is bitwise and must have a bit mask of 256 (0xff).

We can assume that each character is printable, and thus land between 32 and 126 inclusive on the ascii table (if we don't assume this, we can just use 0 through 256 it doesnt speed the code up that much).

Attached is my code for this in `solve2.py`. Sorry for the atrocious code, but it still gets the job done pretty quickly.

From running the code, we find out that there are *two* passwords that can authenticate via this device.

```
l3ak{Sup3r_53cUr3_p4ssw0rD_r1gH7?}
L3AK{B4ckd0or_h1dd3N_iN_H4rDw4Re!}
```

The challenge description mentioned the intended password is `l3ak{...}` and the flag format is `L3AK{...}` so the final flag would be the hidden password: `L3AK{B4ckd0or_h1dd3N_iN_H4rDw4Re!}`.
