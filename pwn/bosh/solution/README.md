# Bosh Solution
### Author: s3af

The solve script connects to the challenge service and sends the ray command to inject arbitrary bytes into memory. We first patch the address 0x133b06c, then assemble the /bin/sh shellcode, writing it one byte at a time starting from 0x1337000. Once the shellcode is set up, we send an echo command to initiate the next step and transition into interactive mode to pop our shell.
