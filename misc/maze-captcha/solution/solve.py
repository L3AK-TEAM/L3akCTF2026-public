#!/usr/bin/env python3
import heapq
import re
import subprocess
import sys

from pwn import context, remote
#wcwidth to get emoji widths
from wcwidth import wcswidth


host = "127.0.0.1"
port = 1337
#maze width
size = 11
cell_width = 3
maze_w = size * (cell_width + 1) + 1
maze_h = size * 2 + 1

#chars for sides of maze
box = set("─│┌┐└┘├┤┬┴┼╶╴╷╵")
#ansi colored terminal stuff
green = "92"
red = "91"
ansiSyntax = re.compile(r"\x1b\[([0-9;]*)([A-Za-z])")
powSyntax = re.compile(rb"proof of work: (.+)\nsolution: ")

def make_weights():
    #chess and dice
    weights = {
        "♙": 1,
        "♘": 3,
        "♗": 3,
        "♖": 5,
        "♕": 9,
        "♔": 100,
        "⚀": 1,
        "⚁": 2,
        "⚂": 3,
        "⚃": 4,
        "⚄": 5,
        "⚅": 6,
    }
    #cards
    for suit in ("🂡🂢🂣🂤🂥🂦🂧🂨🂩🂪🂫🂭🂮", "🂱🂲🂳🂴🂵🂶🂷🂸🂹🂺🂻🂽🂾",
                 "🃑🃒🃓🃔🃕🃖🃗🃘🃙🃚🃛🃝🃞", "🃁🃂🃃🃄🃅🃆🃇🃈🃉🃊🃋🃍🃎"):
        for i, ch in enumerate(suit, 1):
            weights[ch] = min(i, 10)
    #dominos
    for chars, start in (
        ("🁣🁤🁥🁦🁧🁨🁩🁰🁷🁾🂅🂌🂓", 0),
        ("🁪🁫🁬🁭🁮🁯🁶🁽🂄🂋🂒", 1),
        ("🁱🁲🁳🁴🁵🁼🂃🂊🂑", 2),
        ("🁸🁹🁺🁻🂂🂉🂐", 3),
        ("🁿🂀🂁🂈🂏", 4),
        ("🂆🂇🂎", 5),
        ("🂍", 6),
    ):
        for i, ch in enumerate(chars, start):
            weights[ch] = i
    #mahjong
    for suit in ("🀇🀈🀉🀊🀋🀌🀍🀎🀏", "🀐🀑🀒🀓🀔🀕🀖🀗🀘", "🀙🀚🀛🀜🀝🀞🀟🀠🀡"):
        for i, ch in enumerate(suit, 1):
            weights[ch] = i
    return weights


weights = make_weights()

#uses wcswidth to tell the width of smthn on the terminal
def width(s):
    n = wcswidth(s)
    if n >= 0:
        return n
    return len(s)

#converts the colored terminal to visible screen columns and stores the color for entrance/exit searches.. 
def ansi_cells(line):
    cells, color, col, i = [], None, 0, 0
    while i < len(line):
        m = ansiSyntax.match(line, i)
        if m:
            params, cmd = m.groups()
            if cmd == "m":
                codes = params.split(";") if params else ["0"]
                if "0" in codes:
                    color = None
                for code in codes:
                    if code in (green, red, "96", "97"):
                        color = code
            elif cmd == "G":
                col = int(params or "1") - 1
            i = m.end()
            continue

        while len(cells) <= col:
            cells.append((" ", color))
        ch = line[i]
        cells[col] = (ch, color)
        col += max(1, width(ch))
        i += 1
    return cells

#reads a single cell of terminal in format (character,color)
def get(line, col, part=0):
    return line[col][part] if 0 <= col < len(line) else (" " if part == 0 else None)

#the name says it all, it maps out the maze
def parse_maze(data):
    #decodes the ansi-encoding with the aformentioned method
    lines = [ansi_cells(x) for x in data.decode("utf-8", "replace").splitlines()]
    maze = [x for x in lines if any(ch in box for ch, _ in x)][-maze_h:]
    left = min(i for row in maze for i, (ch, _) in enumerate(row) if ch in box)
    maze = [[row[i] if i < len(row) else (" ", None) for i in range(left, left + maze_w)] for row in maze]
    #the cells var stores emoji weights, hwall and vwall are self explanatory
    cells = [[" " for _ in range(size)] for _ in range(size)]
    hwall = [[False for _ in range(size)] for _ in range(size + 1)]
    vwall = [[False for _ in range(size + 1)] for _ in range(size)]
    start = entrance = exit_out = exit_cell = None
    #since every horizontal maze wall is every other line, we can search only that
    for y in range(size + 1):
        row = maze[y * 2]
        for x in range(size):
            cols = range(x * 4 + 1, x * 4 + 1 + cell_width)
            colors = {get(row, c, 1) for c in cols}
            hwall[y][x] = any(get(row, c) != " " for c in cols)
            #checks for entrance and exit color and stores it in very well named variables
            if green in colors or red in colors:
                outside = (x, -1) if y == 0 else (x, size)
                inside = (x, 0) if y == 0 else (x, size - 1)
                if green in colors:
                    start, entrance = outside, inside
                else:
                    exit_out, exit_cell = outside, inside
                hwall[y][x] = False
    #only odd numbered rows contain vertical walls so we only check those
    #legit almost copy paste from the above loop. Same thing but vertical
    for y in range(size):
        row = maze[y*2 + 1]
        for x in range(size + 1):
            col = x*4
            vwall[y][x] = get(row, col) != " "
            if get(row, col, 1) in (green, red):
                outside = (-1, y) if x == 0 else (size, y)
                inside = (0, y) if x == 0 else (size - 1, y)
                if get(row, col, 1) == green:
                    start, entrance = outside, inside
                else:
                    exit_out, exit_cell = outside, inside
                vwall[y][x] = False
        #store emojis weights in cells var
        for x in range(size):
            raw = "".join(get(row, c) for c in range(x*4 + 1, x*4 + 4))
            cells[y][x] = next((ch for ch in raw if ch in weights), " ")

    return cells, hwall, vwall, start, entrance, exit_out, exit_cell

#just checks to see if a move is valid from cell a to b
def open_between(a, b, entrance, exit_cell, start, exit_out, hwall, vwall):
    #start end end are outside the grid so do that first
    if {a, b} in ({start, entrance}, {exit_cell, exit_out}):
        return True
    ax, ay = a
    bx, by = b
    #must stay within two cells inside the maze lol
    if not (0 <= ax < size and 0 <= ay < size and 0 <= bx < size and 0 <= by < size):
        return False
    #moving up or down crosses a hwall
    if ax == bx and abs(ay - by) == 1:
        return not hwall[max(ay, by)][ax]
    #moving left or right crosses a vwall
    if ay == by and abs(ax - bx) == 1:
        return not vwall[ay][max(ax, bx)]
    return False

#returns guess what? the cell cost. 
def cell_cost(pos, cells):
    x, y = pos
    return 0 if not (0 <= x < size and 0 <= y < size) else 1 + weights.get(cells[y][x], 0)

# A* should be faster, but for just an 11x11 maze this is fine and much simpler.
# There are a couple changes, using the walls to prove where to go using the open_between() method above instead of using a linked list or an array or smthn, but the general algorithm is the same.
def dijkstra(parsed):
    cells, hwall, vwall, start, entrance, exit_out, exit_cell = parsed
    dist, prev, heap = {start: 0}, {}, [(0, start)]
    dirs = [("R", 1, 0), ("L", -1, 0), ("D", 0, 1), ("U", 0, -1)]

    while heap:
        cost, pos = heapq.heappop(heap)
        if pos == exit_out:
            break
        if cost != dist[pos]:
            continue
        for move, dx, dy in dirs:
            #nxt = next btw if that wasnt clear
            nxt = (pos[0] + dx, pos[1] + dy)
            #if its a valid move to go to nxt:
            if open_between(pos, nxt, entrance, exit_cell, start, exit_out, hwall, vwall):
                new = cost + cell_cost(nxt, cells)
                if new < dist.get(nxt, 10**9):
                    dist[nxt] = new
                    prev[nxt] = (pos, move)
                    heapq.heappush(heap, (new, nxt))

    path, pos = [], exit_out
    while pos != start:
        pos, move = prev[pos]
        path.append(move)
    return "".join(reversed(path))

#legit just runs whatever pow line the server asks for...
def solve_pow(data):
    m = powSyntax.search(data)
    if not m:
        return b""
    cmd = m.group(1).decode()
    print(f"\n[pow] {cmd}", flush=True)
    return subprocess.check_output(cmd, shell=True, timeout=20).strip()

#prints literally EVERYTHING the server sends to us :)
def show(data):
    sys.stdout.buffer.write(data)
    sys.stdout.buffer.flush()


def main():
    context.log_level = "error"
    io = remote(host, port)
    try:
        #pow line
        data = io.recvuntil((b"solution: ", b"> "), timeout=10)
        show(data)
        if data.endswith(b"solution: "):
            io.sendline(solve_pow(data))
            data = io.recvuntil(b"> ", timeout=10)
            show(data)
        #starts the captcha and solves all 100 rounds
        io.sendline(b"2")
        for _ in range(100):
            data = io.recvuntil(b">", timeout=6)
            show(data)
            io.sendline(dijkstra(parse_maze(data)).encode())
        #PRINT EVERYTHING
        show(io.recvall(timeout=2))
    finally:
        io.close()


if __name__ == "__main__":
    main()