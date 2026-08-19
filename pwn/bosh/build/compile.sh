#!/bin/bash

gcc -c $1 \
    -fPIC \
    -nostdlib \
    -o temp.elf \
    -O2;

objcopy -O binary -j .text temp.elf temp.bin;
python3 makeModule.py "$2" "$3" temp.bin "modules/$2.mod"
rm temp.elf;
