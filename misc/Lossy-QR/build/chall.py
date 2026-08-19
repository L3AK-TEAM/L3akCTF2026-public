#!/usr/bin/env python3

import qrcode
from pyzbar.pyzbar import decode
from pyzbar.wrapper import ZBarSymbol

data = input('Enter data > ').encode()
if not all(32 <= c <= 126 for c in data):
    print('invalid chars')
    exit(1)

img = qrcode.make(data, error_correction=qrcode.constants.ERROR_CORRECT_L)
decoded_objects = decode(img.get_image(), symbols=[ZBarSymbol.QRCODE])
if decoded_objects:
    for decoded_object in decoded_objects:
        if decoded_object.data != data:
            print(open('flag.txt').read())
