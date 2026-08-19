import sys

def p32(x):
    return x.to_bytes(4, "little")


if len(sys.argv) < 5:
    print(len(sys.argv))
    print("Usage: makeModule.py <name> <helpMessage> <codeFile> <outFile>");
    exit()
name = sys.argv[1]
helpmsg = sys.argv[2]
codeFile = open(sys.argv[3], "rb")
code = codeFile.read()



header = p32(len(name)) + p32(len(helpmsg)) + p32(len(code))
body = name.encode() + helpmsg.encode() + code

file = None
file = open(sys.argv[4], "wb")
file.write(header + body)
