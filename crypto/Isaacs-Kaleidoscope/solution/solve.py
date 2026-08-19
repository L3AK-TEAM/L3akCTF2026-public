import base64
import json
import math
import struct
import zlib
from urllib.request import Request, urlopen

def fetch_json(base_url, path, data=None):
    if data is None:
        body = None
        headers = {"Cache-Control": "no-store"}
    else:
        body = json.dumps(data).encode()
        headers = {"Content-Type": "application/json"}

    request = Request(base_url + path, data=body, headers=headers)
    with urlopen(request) as response:
        return json.load(response)

def render_block(base_url, message, block_index):
    result = fetch_json(base_url, "api/render", {
        "message": message,
        "blockIndex": block_index
    })

    if "blocks" not in result or len(result["blocks"]) != 1:
        raise RuntimeError("Focused render did not return exactly one block")

    image = result["blocks"][0]["image"]
    image = image.removeprefix("data:image/png;base64,")
    return base64.b64decode(image)

def paeth_predictor(a, b, c):
    p = a + b - c
    pa = abs(p - a)
    pb = abs(p - b)
    pc = abs(p - c)

    if pa <= pb and pa <= pc:
        return a
    if pb <= pc:
        return b
    return c

def decode_png(buffer):
    if buffer[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError("Invalid PNG signature")

    offset = 8
    width = 0
    height = 0
    bit_depth = 0
    color_type = 0
    idat = []

    while offset < len(buffer):
        length = struct.unpack_from(">I", buffer, offset)[0]
        chunk_type = buffer[offset + 4:offset + 8]
        data = buffer[offset + 8:offset + 8 + length]
        offset += length + 12

        if chunk_type == b"IHDR":
            width, height = struct.unpack_from(">II", data)
            bit_depth = data[8]
            color_type = data[9]
        elif chunk_type == b"IDAT":
            idat.append(data)
        elif chunk_type == b"IEND":
            break

    if bit_depth != 8 or color_type != 6:
        raise ValueError(
            f"Unsupported PNG format: bitDepth={bit_depth}, colorType={color_type}"
        )

    row_length = width * 4
    inflated = zlib.decompress(b"".join(idat))
    pixels = bytearray(width * height * 4)
    input_offset = 0

    for y in range(height):
        filter_type = inflated[input_offset]
        input_offset += 1
        row_offset = y * row_length
        previous_row = row_offset - row_length

        for x in range(row_length):
            raw = inflated[input_offset + x]
            left = pixels[row_offset + x - 4] if x >= 4 else 0
            up = pixels[previous_row + x] if y > 0 else 0
            up_left = pixels[previous_row + x - 4] if y > 0 and x >= 4 else 0

            if filter_type == 0:
                value = raw
            elif filter_type == 1:
                value = raw + left
            elif filter_type == 2:
                value = raw + up
            elif filter_type == 3:
                value = raw + (left + up) // 2
            elif filter_type == 4:
                value = raw + paeth_predictor(left, up, up_left)
            else:
                raise ValueError(f"Unsupported PNG filter: {filter_type}")

            pixels[row_offset + x] = value & 255

        input_offset += row_length

    return {
        "width": width,
        "height": height,
        "data": bytes(pixels)
    }

def rgb_to_hsl(r, g, b):
    r /= 255
    g /= 255
    b /= 255
    highest = max(r, g, b)
    lowest = min(r, g, b)
    lightness = (highest + lowest) / 2
    delta = highest - lowest

    if delta == 0:
        return 0, 0, lightness

    if lightness > 0.5:
        saturation = delta / (2 - highest - lowest)
    else:
        saturation = delta / (highest + lowest)

    if highest == r:
        hue = ((g - b) / delta + (6 if g < b else 0)) * 60
    elif highest == g:
        hue = ((b - r) / delta + 2) * 60
    else:
        hue = ((r - g) / delta + 4) * 60

    return hue, saturation, lightness

def hue_distance(a, b):
    difference = abs(a - b) % 360
    return min(difference, 360 - difference)

def nearest_hue_index(hue, centers):
    return min(range(len(centers)), key=lambda i: hue_distance(hue, centers[i]))

def find_hue_centers(image, count):
    bins = 720
    histogram = [0] * bins

    for i in range(0, len(image["data"]), 4):
        hue, saturation, lightness = rgb_to_hsl(
            image["data"][i],
            image["data"][i + 1],
            image["data"][i + 2]
        )

        if saturation < 0.20 or lightness < 0.12:
            continue

        bin_index = math.floor((hue / 360) * bins + 0.5) % bins
        histogram[bin_index] += saturation

    smoothed = []
    for i in range(bins):
        smoothed.append(sum(histogram[(i + delta) % bins] for delta in range(-3, 4)))

    sorted_bins = sorted(range(bins), key=lambda i: smoothed[i], reverse=True)
    centers = []

    for candidate in sorted_bins:
        hue = candidate / bins * 360
        if all(hue_distance(center, hue) >= 16 for center in centers):
            centers.append(hue)
        if len(centers) == count:
            break

    if len(centers) != count:
        raise RuntimeError(f"Could not find {count} hue clusters; found {len(centers)}")

    for _ in range(6):
        sums = [[0, 0, 0] for _ in centers]

        for bin_index, weight in enumerate(smoothed):
            if weight == 0:
                continue

            hue = bin_index / bins * 360
            center_index = nearest_hue_index(hue, centers)
            radians = math.radians(hue)
            sums[center_index][0] += math.cos(radians) * weight
            sums[center_index][1] += math.sin(radians) * weight
            sums[center_index][2] += weight

        new_centers = []
        for i, (x, y, weight) in enumerate(sums):
            if weight == 0:
                new_centers.append(centers[i])
            else:
                new_centers.append((math.degrees(math.atan2(y, x)) + 360) % 360)

        centers = sorted(new_centers)

    return centers


def pixel_to_complex(x, y, width, height, viewport):
    scale_x = viewport["scale"] * width / height
    scale_y = viewport["scale"]

    return {
        "re": viewport["centerX"] + (x / (width - 1) - 0.5) * scale_x,
        "im": viewport["centerY"] + (0.5 - y / (height - 1)) * scale_y
    }

def estimate_roots(image, hue_centers, viewport):
    groups = []
    for _ in hue_centers:
        groups.append({
            "max_light": -1,
            "points": [],
            "marker_points": []
        })

    for pixel in range(image["width"] * image["height"]):
        offset = pixel * 4
        hue, saturation, lightness = rgb_to_hsl(
            image["data"][offset],
            image["data"][offset + 1],
            image["data"][offset + 2]
        )

        if saturation < 0.18 or lightness < 0.14:
            continue

        label = nearest_hue_index(hue, hue_centers)
        point = (pixel % image["width"], pixel // image["width"], lightness)

        if lightness >= 0.68:
            groups[label]["marker_points"].append(point)

        if lightness > groups[label]["max_light"] + 0.002:
            groups[label]["max_light"] = lightness
            groups[label]["points"] = [point]
        elif lightness >= groups[label]["max_light"] - 0.002:
            groups[label]["points"].append(point)

    roots = []

    for label, group in enumerate(groups):
        points = group["marker_points"] or group["points"]
        if not points:
            raise RuntimeError(f"Could not estimate root for hue cluster {label}")

        total_weight = 0
        x_total = 0
        y_total = 0

        for x, y, lightness in points:
            weight = max(0.001, lightness ** 8)
            x_total += x * weight
            y_total += y * weight
            total_weight += weight

        roots.append(pixel_to_complex(
            x_total / total_weight,
            y_total / total_weight,
            image["width"],
            image["height"],
            viewport
        ))

    return roots

def get_signature(base_url, challenge, message, block_index):
    png = render_block(base_url, message, block_index)
    image = decode_png(png)
    config = challenge["publicConfig"]
    hue_centers = find_hue_centers(image, config["polynomialDegree"])
    return estimate_roots(image, hue_centers, config["viewport"])

def root_set_distance(a, b):
    count = min(len(a), len(b))
    used = [False] * count
    best = math.inf

    def search(index, total):
        nonlocal best

        if total >= best:
            return
        if index == count:
            best = total
            return

        for j in range(count):
            if used[j]:
                continue

            used[j] = True
            real_difference = a[index]["re"] - b[j]["re"]
            imaginary_difference = a[index]["im"] - b[j]["im"]
            search(
                index + 1,
                total + real_difference ** 2 + imaginary_difference ** 2
            )
            used[j] = False

    search(0, 0)
    return math.sqrt(best / max(1, count))

def show_byte(value):
    code = ord(value[0])
    if 32 <= code <= 126:
        return json.dumps(value)
    return f"0x{code:02x}"

def recover_flag():
    base_url = "[insert challenge url here]/"
    candidates = [chr(code) for code in range(32, 127)]
    candidates += [chr(code) for code in range(1, 32)]
    max_length = 96
    exhaustive = False

    candidates = list(dict.fromkeys(candidates))
    challenge = fetch_json(base_url, "api/challenge")
    block_size = challenge["publicConfig"]["blockSize"]
    recovered = ""

    print(f"Connected to {base_url}")
    print(f"Block size: {block_size}")
    print(f"Polynomial degree: {challenge['publicConfig']['polynomialDegree']}")
    print(f"Candidate byte count: {len(candidates)}")

    for index in range(max_length):
        pad_length = block_size - 1 - index % block_size
        prefix = "A" * pad_length
        block_index = index // block_size
        target = get_signature(base_url, challenge, prefix, block_index)
        scores = []

        for candidate in candidates:
            probe = prefix + recovered + candidate
            signature = get_signature(base_url, challenge, probe, block_index)
            distance = root_set_distance(target, signature)
            scores.append((candidate, distance))

            if not exhaustive and distance < 0.0001:
                break

        scores.sort(key=lambda score: score[1])
        best_candidate, best_distance = scores[0]
        second_distance = scores[1][1] if len(scores) > 1 else None

        if best_candidate == "\x01":
            next_recovered = recovered
        else:
            next_recovered = recovered + best_candidate

        if second_distance is None:
            margin = "early"
        else:
            margin = f"{second_distance - best_distance:.4f}"

        print(
            f"{index:02d}: {show_byte(best_candidate)} "
            f"distance={best_distance:.4f} margin={margin} flag={next_recovered}"
        )

        if best_candidate == "\x01":
            print("Reached PKCS#7 padding")
            break

        recovered = next_recovered

    return recovered

flag = recover_flag()
print(f"\nRecovered flag: {flag}")
