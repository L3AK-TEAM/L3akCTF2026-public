from Crypto.Util.number import *

def _solve_28_to_33(one, two, three, four, five, six, seven, eight, nine, ten, eleven, twelve, thirteen, fourteen, fifteen, sixteen, seventeen, eighteen, nineteen, twenty, twentyone, twentytwo, twentythree, twentyfour, twentyfive, twentysix, twentyseven, thirtyfour):
	for twentyeight in range(32,127):
		if ((twentyeight ^ (((three >> 5) * (((1 << 1) | (1 << 2)) | (1 << 3))) % 256)) == 0x58):
			for twentynine in range(32,127):
				if (((twentynine + ((four >> 5) * (((1 << 1) | (1 << 2)) | (1 << 6)))) % 256) == 0x03):
					for thirty in range(32,127):
						if (((thirty - ((one >> 5) * (((1 | (1 << 1)) | (1 << 4)) | (1 << 5)))) % 256) == 0xCE):
							for thirtyone in range(32,127):
								if (((thirtyone + ((three >> 5) * ((1 << 1) | (1 << 3)))) % 256) == 0x66):
									for thirtytwo in range(32,127):
										if ((thirtytwo ^ (((four >> 5) * (((1 << 1) | (1 << 4)) | (1 << 6))) % 256)) == 0xC1):
											for thirtythree in range(32,127):
												if ((thirtythree ^ (((one >> 5) * ((1 << 1) | (1 << 2))) % 256)) == 0x2D):
													print(long_to_bytes(one) + long_to_bytes(two) + long_to_bytes(three) + long_to_bytes(four) + long_to_bytes(five) + long_to_bytes(six) + long_to_bytes(seven) + long_to_bytes(eight) + long_to_bytes(nine) + long_to_bytes(ten) + long_to_bytes(eleven) + long_to_bytes(twelve) + long_to_bytes(thirteen) + long_to_bytes(fourteen) + long_to_bytes(fifteen) + long_to_bytes(sixteen) + long_to_bytes(seventeen) + long_to_bytes(eighteen) + long_to_bytes(nineteen) + long_to_bytes(twenty) + long_to_bytes(twentyone) + long_to_bytes(twentytwo) + long_to_bytes(twentythree) + long_to_bytes(twentyfour) + long_to_bytes(twentyfive) + long_to_bytes(twentysix) + long_to_bytes(twentyseven) + long_to_bytes(twentyeight) + long_to_bytes(twentynine) + long_to_bytes(thirty) + long_to_bytes(thirtyone) + long_to_bytes(thirtytwo) + long_to_bytes(thirtythree) + long_to_bytes(thirtyfour))

def _solve_20_to_27(one, two, three, four, five, six, seven, eight, nine, ten, eleven, twelve, thirteen, fourteen, fifteen, sixteen, seventeen, eighteen, nineteen, thirtyfour):
	for twenty in range(32,127):
		if (((twenty + ((four >> 5) * (((1 << 1) | (1 << 3)) | (1 << 4)))) % 256) == 0x82):
			for twentyone in range(32,127):
				if (((twentyone - ((one >> 5) * ((1 << 2) | (1 << 4)))) % 256) == 0x37):
					for twentytwo in range(32,127):
						if (((twentytwo - ((three >> 5) * ((1 << 1) | (1 << 3)))) % 256) == 0x55):
							for twentythree in range(32,127):
								if (((twentythree - ((four >> 5) * ((1 | (1 << 3)) | (1 << 5)))) % 256) == 0xFC):
									for twentyfour in range(32,127):
										if (((twentyfour - ((one >> 5) * (((1 | (1 << 4)) | (1 << 6)) | (1 << 7)))) % 256) == 0xBD):
											for twentyfive in range(32,127):
												if (((twentyfive - ((three >> 5) * (((1 << 1) | (1 << 3)) | (1 << 5)))) % 256) == 0xF4):
													for twentysix in range(32,127):
														if (((twentysix - ((four >> 5) * (1 << 4))) % 256) == 0x14):
															for twentyseven in range(32,127):
																if (((twentyseven + ((one >> 5) * ((1 | (1 << 1)) | (1 << 4)))) % 256) == 0x98):
																	_solve_28_to_33(one, two, three, four, five, six, seven, eight, nine, ten, eleven, twelve, thirteen, fourteen, fifteen, sixteen, seventeen, eighteen, nineteen, twenty, twentyone, twentytwo, twentythree, twentyfour, twentyfive, twentysix, twentyseven, thirtyfour)

def _solve_12_to_19(one, two, three, four, five, six, seven, eight, nine, ten, eleven, thirtyfour):
	for twelve in range(32,127):
		if (((twelve + ((one >> 5) * ((((1 << 1) | (1 << 3)) | (1 << 4)) | (1 << 5)))) % 256) == 0xE3):
			for thirteen in range(32,127):
				if ((thirteen ^ (((three >> 5) * (1 | (1 << 6))) % 256)) == 0xF0):
					for fourteen in range(32,127):
						if (((fourteen - ((four >> 5) * (1 << 2))) % 256) == 0x57):
							for fifteen in range(32,127):
								if (((fifteen + ((one >> 5) * ((1 | (1 << 1)) | (1 << 4)))) % 256) == 0x8E):
									for sixteen in range(32,127):
										if (((sixteen - ((three >> 5) * (1 | (1 << 6)))) % 256) == 0xAF):
											for seventeen in range(32,127):
												if (((seventeen + ((four >> 5) * ((1 | (1 << 4)) | (1 << 5)))) % 256) == 0xC6):
													for eighteen in range(32,127):
														if (((eighteen + ((one >> 5) * (1 | (1 << 2)))) % 256) == 0x6E):
															for nineteen in range(32,127):
																if (((nineteen + ((three >> 5) * (((1 | (1 << 1)) | (1 << 6)) | (1 << 7)))) % 256) == 0xB9):
																	_solve_20_to_27(one, two, three, four, five, six, seven, eight, nine, ten, eleven, twelve, thirteen, fourteen, fifteen, sixteen, seventeen, eighteen, nineteen, thirtyfour)

def _solve_5_to_11(one, two, three, four):
	for thirtyfour in range(32,127):
		if (((thirtyfour - (one ^ three)) % 256) == 0x70):
			for five in range(32,127):
				if ((five ^ thirtyfour) == 0x06):
					for six in range(32,127):
						if (((six - ((one >> 5) * (1 | (1 << 4)))) % 256) == 0x20):
							for seven in range(32,127):
								if (((seven - ((three >> 5) * (1 | (1 << 6)))) % 256) == 0xB2):
									for eight in range(32,127):
										if (((eight - ((four >> 5) * ((1 | (1 << 2)) | (1 << 3)))) % 256) == 0x49):
											for nine in range(32,127):
												if (((nine + ((one >> 5) * (((1 << 3) | (1 << 4)) | (1 << 5)))) % 256) == 0xDB):
													for ten in range(32,127):
														if (((ten - ((three >> 5) * (((1 << 1) | (1 << 2)) | (1 << 3)))) % 256) == 0x48):
															for eleven in range(32,127):
																if (((eleven + ((four >> 5) * (((1 | (1 << 4)) | (1 << 6)) | (1 << 7)))) % 256) == 0xD2):
																	_solve_12_to_19(one, two, three, four, five, six, seven, eight, nine, ten, eleven, thirtyfour)

def solve(format):
	format = format.encode()
	one = format[0]
	two = format[1]
	three = format[2]
	four = format[3]
	_solve_5_to_11(one, two, three, four)

solve("l3ak")
solve("L3AK")
