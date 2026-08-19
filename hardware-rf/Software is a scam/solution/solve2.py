from Crypto.Util.number import *

for ten in range(32,127):
	for fifteen in range(32,127):
		if ((ten + fifteen)%256 < 0xd6):
			if ((ten + fifteen)%256 > 0xbd):
				for five in range(32,127):
					for twenty in range(32,127):
						if ((five - twenty)%256 == 0xfe):
							if (((ten & twenty) ^ (~(five))%256) == 0xd9):
								if (((five & ten) & (~(twenty ^ fifteen))) == 0x59):
									print(b'????' + long_to_bytes(five) + b'????' + long_to_bytes(ten) + b'????'  + long_to_bytes(fifteen) +  b'????' + long_to_bytes(twenty))



