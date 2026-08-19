from Crypto.Util.number import *

for six in range(32,127):
	for thirteen in range(32,127):
		if (((six + thirteen)%256) == 0xb5):
			for eight in range(32,127):
				if (((thirteen - eight)%256) == 0x2e):
					for sixteen in range(32,127):
						if (sixteen ^ eight == 0x2c):
							for seventeen in range(32,127):
								if (seventeen - eight)%256 == 0xef:
									for twelve in range(32,127):
										for seven in range(32,127):
											if ((seven - ((~(((six << 2)%256) & twelve))%256))%256 == 0x74):
												for nine in range(32,127):
													if ((~(((((nine & thirteen) ^ ((~(nine & sixteen))%256)) ^ sixteen ^ twelve) & ~(((nine & thirteen) ^ ((~(nine & sixteen))%256)) & sixteen & twelve)))%256) == seven):
														for fourteen in range(32,127):
															if ((fourteen ^ (twelve ^ (seventeen & ((~(nine & sixteen))%256)))) == 0x51):
																for eighteen in range(32,127):
																	if ((((seventeen - eighteen)%256) & nine) == 0x33):
																		for eleven in range(32,127):
																			if (((((~(((~((((six << 2)%256) ^ eleven ^ thirteen) & ~(((six << 2) % 256) & eleven & thirteen))) % 256) & fourteen)) % 256) ^ ((~((((six << 2) % 256) ^ eleven ^ thirteen) & ~(((six << 2) % 256) & eleven & thirteen))) % 256)) | eighteen) == 0x37):
																				for nineteen in range(32,127):
																					if (((((~((((six << 2)%256) ^ eleven ^ thirteen) & ~(((six << 2)%256) & eleven & thirteen)))%256) + nineteen)%256) == 0xd):
																						if ((((nine ^ nineteen) + eighteen)%256) == 0xab):
																							print(b'?????' + long_to_bytes(six) + long_to_bytes(seven) + long_to_bytes(eight) + long_to_bytes(nine) + b'?' + long_to_bytes(eleven) + long_to_bytes(twelve) + long_to_bytes(thirteen) + long_to_bytes(fourteen) + b'?' + long_to_bytes(sixteen) + long_to_bytes(seventeen) + long_to_bytes(eighteen) + long_to_bytes(nineteen) + b'?')
