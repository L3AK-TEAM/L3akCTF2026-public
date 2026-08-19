from pathlib import Path
import mpmath as mp

mp.mp.dps = 900

def parse_params(text):
    params = {}
    for line in text.splitlines():
        if not line.strip().lower().startswith(".param"):
            continue
        for item in line.split()[1:]:
            if "=" not in item:
                continue
            name, value = item.split("=", 1)
            if not value.endswith(("u", "f")):
                params[name] = mp.mpf(value)
    return params

def resistor_gain(text, params):
    resistors = []
    for line in text.splitlines():
        if not line or line[0] in "*.+":
            continue
        fields = line.split()
        name = fields[0].upper()
        numbered_resistor = len(name) == 4 and name[0] == "R" and name[1:].isdigit()
        if numbered_resistor or name == "R_U1_BIAS":
            value = fields[3]
            if value.startswith("{"):
                value = params[value[1:-1]]
            else:
                value = mp.mpf(value)
            resistors.append((fields[1], fields[2], value))

    nodes = sorted({node for a, b, _ in resistors for node in (a, b)} - {"0", "circus_dac"})
    positions = {node: i for i, node in enumerate(nodes)}
    known = {"0": mp.mpf(0), "circus_dac": mp.mpf(1)}
    matrix = mp.matrix(len(nodes), len(nodes))
    result = mp.matrix(len(nodes), 1)

    for a, b, resistance in resistors:
        conductance = 1 / resistance
        for node, other in ((a, b), (b, a)):
            if node not in positions:
                continue
            row = positions[node]
            matrix[row, row] += conductance
            if other in positions:
                matrix[row, positions[other]] -= conductance
            else:
                result[row] += conductance * known[other]
    voltages = mp.lu_solve(matrix, result)
    return voltages[positions["net_tap"]]

def noninverting_gain(a, rg, rf):
    return a / (1 + a * rg / (rg + rf))

def inverting_gain(a, rin, rf):
    return -(a * rf) / (rf + rin * (a + 1))

def mirror_gain(sign, params, name):
    ratio = (params[name + "_WO"] / params[name + "_LO"])
    ratio /= params[name + "_WR"] / params[name + "_LR"]
    return sign * ratio * params[name + "_RLOAD"] / params[name + "_RSET"]

def main():
    folder = './digital-is-a-scam/'
    netlist = (folder + "digital_is_a_scam.spice").read_text()
    measured = mp.mpf((folder + "output.txt").read_text().strip())
    params = parse_params(netlist)

    bit_count = None
    flags = []

    for line in netlist.splitlines():
        if "N_BITS" in line and "=" in line:
            value = line.split("N_BITS", 1)[1].split("=", 1)[1].strip().split()[0]
            if value.isdigit():
                bit_count = int(value)
        for word in line.split():
            if len(word) == 7 and word.startswith("flag") and word[4:].isdigit():
                flags.append(int(word[4:]))

    if bit_count is None:
        bit_count = max(flags) + 1

    gain = resistor_gain(netlist, params)
    gain *= noninverting_gain(params["U1_A"], params["U1_RG"], params["U1_RF"])
    gain *= mirror_gain(-1, params, "CM1")
    gain *= inverting_gain(params["U2_A"], params["U2_RIN"], params["U2_RF"])
    gain *= mirror_gain(1, params, "CM2")
    gain *= noninverting_gain(params["U3_A"], params["U3_RG"], params["U3_RF"])
    gain *= mirror_gain(-1, params, "CM3")
    gain *= inverting_gain(params["U4_A"], params["U4_RIN"], params["U4_RF"])

    secret = int(mp.floor(measured / gain * mp.power(2, bit_count) + mp.mpf("0.5")))
    print(secret.to_bytes(bit_count // 8, "big").decode())

if __name__ == "__main__":
    main()
