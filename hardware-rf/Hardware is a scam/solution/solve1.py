from Crypto.Util.number import *

for one in range(32,127):
	for three in range(32,127):
		if ((three - one)%256 > 0xf4):
			for two in range(32,127):
				for four in range(32,127):
					if (((one ^ two) ^ three) == 0x3e):
						if (three ^ four == 0xa):
							if ((~(((((one * four)%256) + one)%256)^two))%256 == 0x5c):
								if ((~((one & three) | (two^four)))%256 == 0x87):
									print(long_to_bytes(one) + long_to_bytes(two) +long_to_bytes(three) + long_to_bytes(four) + b'?'*30)
