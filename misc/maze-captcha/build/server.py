#!/usr/bin/env python3
import base64
import binascii
import contextlib
import heapq
import os
import random
import secrets
import socketserver
import struct
import time
from dataclasses import dataclass

try:
    from wcwidth import wcswidth
except ImportError:
    wcswidth = None


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
HOST = os.environ.get("HOST", "127.0.0.1")
PORT = int(os.environ.get("PORT", "1337"))
SIZE = 11
ROUNDS = 100
ROUND_SECONDS = 5
CELL_WIDTH = 3
OUTSIDE_WIDTH = 6
POW_DIFFICULTY = int(os.environ.get("POW_DIFFICULTY", "5000"))

RESET = "\033[0m"
WHITE = "\033[97m"
RED = "\033[91m"
GREEN = "\033[92m"
LIGHT_BLUE = "\033[96m"

WALL = "#"
EMPTY = " "
ROBOT = "🤖"
POW_MOD = (1 << 1279) - 1
POW_EXP = 1 << 1277


EMOJI_WEIGHTS = {
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

for i, emoji in enumerate("🂡🂢🂣🂤🂥🂦🂧🂨🂩🂪🂫🂭🂮", start=1):
    EMOJI_WEIGHTS[emoji] = min(i, 10)
for i, emoji in enumerate("🂱🂲🂳🂴🂵🂶🂷🂸🂹🂺🂻🂽🂾", start=1):
    EMOJI_WEIGHTS[emoji] = min(i, 10)
for i, emoji in enumerate("🃑🃒🃓🃔🃕🃖🃗🃘🃙🃚🃛🃝🃞", start=1):
    EMOJI_WEIGHTS[emoji] = min(i, 10)
for i, emoji in enumerate("🃁🃂🃃🃄🃅🃆🃇🃈🃉🃊🃋🃍🃎", start=1):
    EMOJI_WEIGHTS[emoji] = min(i, 10)

for i, emoji in enumerate("🁣🁤🁥🁦🁧🁨🁩🁰🁷🁾🂅🂌🂓"):
    EMOJI_WEIGHTS[emoji] = i
for i, emoji in enumerate("🁪🁫🁬🁭🁮🁯🁶🁽🂄🂋🂒", start=1):
    EMOJI_WEIGHTS[emoji] = i
for i, emoji in enumerate("🁱🁲🁳🁴🁵🁼🂃🂊🂑", start=2):
    EMOJI_WEIGHTS[emoji] = i
for i, emoji in enumerate("🁸🁹🁺🁻🂂🂉🂐", start=3):
    EMOJI_WEIGHTS[emoji] = i
for i, emoji in enumerate("🁿🂀🂁🂈🂏", start=4):
    EMOJI_WEIGHTS[emoji] = i
for i, emoji in enumerate("🂆🂇🂎", start=5):
    EMOJI_WEIGHTS[emoji] = i
for emoji, weight in zip("🂍", [6]):
    EMOJI_WEIGHTS[emoji] = weight

for i, emoji in enumerate("🀇🀈🀉🀊🀋🀌🀍🀎🀏", start=1):
    EMOJI_WEIGHTS[emoji] = i
for i, emoji in enumerate("🀐🀑🀒🀓🀔🀕🀖🀗🀘", start=1):
    EMOJI_WEIGHTS[emoji] = i
for i, emoji in enumerate("🀙🀚🀛🀜🀝🀞🀟🀠🀡", start=1):
    EMOJI_WEIGHTS[emoji] = i

LOW_EMOJIS = [emoji for emoji, weight in EMOJI_WEIGHTS.items() if weight <= 3]
HIGH_EMOJIS = [emoji for emoji, weight in EMOJI_WEIGHTS.items() if weight >= 9]


@dataclass(frozen=True)
class Maze:
    cells: list[list[str]]
    h_walls: list[list[bool]]
    v_walls: list[list[bool]]
    start_outside: tuple[int, int]
    exit_outside: tuple[int, int]
    entrance: tuple[int, int]
    exit: tuple[int, int]
    optimal_score: int


def emoji_color(emoji: str) -> str:
    code = ord(emoji[0])
    if 0x1F0B1 <= code <= 0x1F0BE or 0x1F0C1 <= code <= 0x1F0CE:
        return RED
    if 0x1F007 <= code <= 0x1F00F:
        return RED
    if 0x1F010 <= code <= 0x1F018:
        return GREEN
    if 0x1F019 <= code <= 0x1F021:
        return LIGHT_BLUE
    return WHITE


def wall_char(char: str, color: str = WHITE) -> str:
    return f"{color}{char}{RESET}"


def cell_text(tile: str) -> str:
    if tile == EMPTY:
        return " " * CELL_WIDTH
    if tile == ROBOT:
        width = display_width(tile)
        return f"{WHITE}{tile}{RESET}{' ' * max(0, CELL_WIDTH - width)}"
    width = display_width(tile)
    left_pad = max(0, (CELL_WIDTH - width) // 2)
    right_pad = max(0, CELL_WIDTH - width - left_pad)
    return f"{' ' * left_pad}{emoji_color(tile)}{tile}{RESET}{' ' * right_pad}"


def display_width(text: str) -> int:
    if wcswidth is not None:
        width = wcswidth(text)
        if width >= 0:
            return width
    return len(text)


def render(maze: Maze, round_no: int) -> str:
    lines = [
        f"Round {round_no}/{ROUNDS}",
        "Solve the maze with the least points.",
        "",
    ]
    lines.extend(render_maze_lines(maze))
    lines.append("")
    lines.append(">")
    return "\n".join(lines)


def render_maze_lines(maze: Maze) -> list[str]:
    maze_lines = [render_wall_row(maze, 0)]
    for y in range(SIZE):
        maze_lines.append(render_cell_row(maze, y))
        maze_lines.append(render_wall_row(maze, y + 1))

    if maze.start_outside[1] == -1:
        return [top_robot_line(maze)] + [outside_blank() + line for line in maze_lines]
    if maze.start_outside[1] == SIZE:
        return [outside_blank() + line for line in maze_lines] + [bottom_robot_line(maze)]
    if maze.start_outside[0] == -1:
        start_y = maze.start_outside[1]
        rendered = []
        for index, line in enumerate(maze_lines):
            if index == 1 + start_y * 2:
                rendered.append(left_robot_prefix() + line)
            else:
                rendered.append(outside_blank() + line)
        return rendered
    if maze.start_outside[0] == SIZE:
        start_y = maze.start_outside[1]
        rendered = []
        for index, line in enumerate(maze_lines):
            if index == 1 + start_y * 2:
                rendered.append(outside_blank() + line + right_robot_suffix())
            else:
                rendered.append(outside_blank() + line + outside_blank())
        return rendered
    return [outside_blank() + line for line in maze_lines]


def top_robot_line(maze: Maze) -> str:
    start_x = maze.start_outside[0]
    offset = OUTSIDE_WIDTH + start_x * (CELL_WIDTH + 1) + 1
    target_width = OUTSIDE_WIDTH + rendered_maze_width()
    suffix_width = max(0, target_width - offset - OUTSIDE_WIDTH)
    return " " * offset + robot_field() + " " * suffix_width


def bottom_robot_line(maze: Maze) -> str:
    return top_robot_line(maze)


def rendered_maze_width() -> int:
    return SIZE * (CELL_WIDTH + 1) + 1


def robot_field() -> str:
    width = display_width(ROBOT)
    return f"{WHITE}{ROBOT}{RESET}{' ' * max(0, OUTSIDE_WIDTH - width)}"


def left_robot_prefix() -> str:
    return f"{WHITE}{ROBOT}{RESET}\033[{OUTSIDE_WIDTH + 1}G"


def right_robot_suffix() -> str:
    return robot_field()


def outside_blank() -> str:
    return " " * OUTSIDE_WIDTH


def render_wall_row(maze: Maze, y: int) -> str:
    line = []
    for x in range(SIZE):
        line.append(wall_char(junction_char(maze, x, y), junction_color(maze, x, y)))
        if display_h_wall(maze, y, x):
            line.append(wall_char("─" * CELL_WIDTH, horizontal_wall_color(maze, y, x)))
        else:
            line.append(" " * CELL_WIDTH)
    line.append(wall_char(junction_char(maze, SIZE, y), junction_color(maze, SIZE, y)))
    return "".join(line)


def render_cell_row(maze: Maze, y: int) -> str:
    line = []
    for x in range(SIZE):
        if display_v_wall(maze, y, x):
            line.append(wall_char("│", vertical_wall_color(maze, y, x)))
        else:
            line.append(" ")
        line.append(cell_text(maze.cells[y][x]))
    if display_v_wall(maze, y, SIZE):
        line.append(wall_char("│", vertical_wall_color(maze, y, SIZE)))
    else:
        line.append(" ")
    return "".join(line)


def display_h_wall(maze: Maze, y: int, x: int) -> bool:
    return maze.h_walls[y][x] or horizontal_boundary_opening(maze, y, x)


def display_v_wall(maze: Maze, y: int, x: int) -> bool:
    return maze.v_walls[y][x] or vertical_boundary_opening(maze, y, x)


def horizontal_boundary_opening(maze: Maze, y: int, x: int) -> bool:
    return boundary_kind_for_h_segment(maze, y, x) is not None


def vertical_boundary_opening(maze: Maze, y: int, x: int) -> bool:
    return boundary_kind_for_v_segment(maze, y, x) is not None


def horizontal_wall_color(maze: Maze, y: int, x: int) -> str:
    kind = boundary_kind_for_h_segment(maze, y, x)
    if kind == "start":
        return GREEN
    if kind == "exit":
        return RED
    return WHITE


def vertical_wall_color(maze: Maze, y: int, x: int) -> str:
    kind = boundary_kind_for_v_segment(maze, y, x)
    if kind == "start":
        return GREEN
    if kind == "exit":
        return RED
    return WHITE


def junction_color(maze: Maze, x: int, y: int) -> str:
    if junction_touches_boundary_kind(maze, x, y, "start"):
        return GREEN
    if junction_touches_boundary_kind(maze, x, y, "exit"):
        return RED
    return WHITE


def boundary_kind_for_h_segment(maze: Maze, y: int, x: int) -> str | None:
    if y == 0:
        if maze.start_outside == (x, -1):
            return "start"
        if maze.exit_outside == (x, -1):
            return "exit"
    if y == SIZE:
        if maze.start_outside == (x, SIZE):
            return "start"
        if maze.exit_outside == (x, SIZE):
            return "exit"
    return None


def boundary_kind_for_v_segment(maze: Maze, y: int, x: int) -> str | None:
    if x == 0:
        if maze.start_outside == (-1, y):
            return "start"
        if maze.exit_outside == (-1, y):
            return "exit"
    if x == SIZE:
        if maze.start_outside == (SIZE, y):
            return "start"
        if maze.exit_outside == (SIZE, y):
            return "exit"
    return None


def junction_touches_boundary_kind(maze: Maze, x: int, y: int, kind: str) -> bool:
    if x > 0 and boundary_kind_for_h_segment(maze, y, x - 1) == kind:
        return True
    if x < SIZE and boundary_kind_for_h_segment(maze, y, x) == kind:
        return True
    if y > 0 and boundary_kind_for_v_segment(maze, y - 1, x) == kind:
        return True
    if y < SIZE and boundary_kind_for_v_segment(maze, y, x) == kind:
        return True
    return False


def junction_char(maze: Maze, x: int, y: int) -> str:
    up = y > 0 and display_v_wall(maze, y - 1, x)
    down = y < SIZE and display_v_wall(maze, y, x)
    left = x > 0 and display_h_wall(maze, y, x - 1)
    right = x < SIZE and display_h_wall(maze, y, x)
    return BOX_CHARS[(up, down, left, right)]


BOX_CHARS = {
    (False, False, False, False): " ",
    (False, False, False, True): "╶",
    (False, False, True, False): "╴",
    (False, False, True, True): "─",
    (False, True, False, False): "╷",
    (False, True, False, True): "┌",
    (False, True, True, False): "┐",
    (False, True, True, True): "┬",
    (True, False, False, False): "╵",
    (True, False, False, True): "└",
    (True, False, True, False): "┘",
    (True, False, True, True): "┴",
    (True, True, False, False): "│",
    (True, True, False, True): "├",
    (True, True, True, False): "┤",
    (True, True, True, True): "┼",
}


def make_maze() -> Maze:
    while True:
        maze = _make_candidate()
        optimal_score, optimal_paths = solve_optimal(maze)
        route_count = count_routes(maze, limit=7)
        if 2 <= route_count <= 6 and optimal_paths == 1:
            return Maze(
                maze.cells,
                maze.h_walls,
                maze.v_walls,
                maze.start_outside,
                maze.exit_outside,
                maze.entrance,
                maze.exit,
                optimal_score,
            )


def _make_candidate() -> Maze:
    cells = [[EMPTY for _ in range(SIZE)] for _ in range(SIZE)]
    h_walls = [[True for _ in range(SIZE)] for _ in range(SIZE + 1)]
    v_walls = [[True for _ in range(SIZE + 1)] for _ in range(SIZE)]

    carve_perfect_maze(h_walls, v_walls)
    open_extra_walls(h_walls, v_walls, random.randint(1, 5))

    side = random.choice(["left", "right", "top", "bottom"])
    if side in ("left", "right"):
        start_y = random.randrange(SIZE)
        exit_y = random.randrange(SIZE)
        if side == "left":
            entrance = (0, start_y)
            exit_tile = (SIZE - 1, exit_y)
            start_outside = (-1, start_y)
            exit_outside = (SIZE, exit_y)
            v_walls[start_y][0] = False
            v_walls[exit_y][SIZE] = False
        else:
            entrance = (SIZE - 1, start_y)
            exit_tile = (0, exit_y)
            start_outside = (SIZE, start_y)
            exit_outside = (-1, exit_y)
            v_walls[start_y][SIZE] = False
            v_walls[exit_y][0] = False
    else:
        start_x = random.randrange(SIZE)
        exit_x = random.randrange(SIZE)
        if side == "top":
            entrance = (start_x, 0)
            exit_tile = (exit_x, SIZE - 1)
            start_outside = (start_x, -1)
            exit_outside = (exit_x, SIZE)
            h_walls[0][start_x] = False
            h_walls[SIZE][exit_x] = False
        else:
            entrance = (start_x, SIZE - 1)
            exit_tile = (exit_x, 0)
            start_outside = (start_x, SIZE)
            exit_outside = (exit_x, -1)
            h_walls[SIZE][start_x] = False
            h_walls[0][exit_x] = False

    maze = Maze(cells, h_walls, v_walls, start_outside, exit_outside, entrance, exit_tile, 0)
    cheap_path = shortest_cell_path(maze)
    place_emojis(cells, set(cheap_path), entrance)
    return maze


def carve_perfect_maze(h_walls: list[list[bool]], v_walls: list[list[bool]]) -> None:
    start = (random.randrange(SIZE), random.randrange(SIZE))
    visited = {start}
    stack = [start]

    while stack:
        x, y = stack[-1]
        options = []
        for nx, ny in cell_neighbors((x, y)):
            if (nx, ny) not in visited:
                options.append((nx, ny))
        if not options:
            stack.pop()
            continue
        nx, ny = random.choice(options)
        remove_wall_between(h_walls, v_walls, (x, y), (nx, ny))
        visited.add((nx, ny))
        stack.append((nx, ny))


def open_extra_walls(h_walls: list[list[bool]], v_walls: list[list[bool]], count: int) -> None:
    candidates = []
    for y in range(SIZE):
        for x in range(SIZE):
            if x + 1 < SIZE and v_walls[y][x + 1]:
                candidates.append(((x, y), (x + 1, y)))
            if y + 1 < SIZE and h_walls[y + 1][x]:
                candidates.append(((x, y), (x, y + 1)))
    random.shuffle(candidates)
    for a, b in candidates[:count]:
        remove_wall_between(h_walls, v_walls, a, b)


def remove_wall_between(
    h_walls: list[list[bool]],
    v_walls: list[list[bool]],
    a: tuple[int, int],
    b: tuple[int, int],
) -> None:
    ax, ay = a
    bx, by = b
    if ax == bx:
        h_walls[max(ay, by)][ax] = False
    else:
        v_walls[ay][max(ax, bx)] = False


def cell_neighbors(pos: tuple[int, int]):
    x, y = pos
    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        nx, ny = x + dx, y + dy
        if 0 <= nx < SIZE and 0 <= ny < SIZE:
            yield nx, ny


def place_emojis(
    cells: list[list[str]],
    cheap_path: set[tuple[int, int]],
    entrance: tuple[int, int],
) -> None:
    for y in range(SIZE):
        for x in range(SIZE):
            if (x, y) == entrance:
                continue
            if random.random() > 0.38:
                continue
            cells[y][x] = random.choice(LOW_EMOJIS if (x, y) in cheap_path else HIGH_EMOJIS)


def passable(maze: Maze, pos: tuple[int, int]) -> bool:
    x, y = pos
    if pos in (maze.start_outside, maze.exit_outside):
        return True
    return 0 <= x < SIZE and 0 <= y < SIZE


def step_cost(maze: Maze, pos: tuple[int, int]) -> int:
    x, y = pos
    if not (0 <= x < SIZE and 0 <= y < SIZE):
        return 0
    return 1 + EMOJI_WEIGHTS.get(maze.cells[y][x], 0)


def neighbors(maze: Maze, pos: tuple[int, int]):
    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        nxt = (pos[0] + dx, pos[1] + dy)
        if passable(maze, nxt) and open_between(maze, pos, nxt):
            yield nxt


def open_between(maze: Maze, a: tuple[int, int], b: tuple[int, int]) -> bool:
    if a == maze.start_outside and b == maze.entrance:
        return True
    if b == maze.start_outside and a == maze.entrance:
        return True
    if a == maze.exit and b == maze.exit_outside:
        return True
    if b == maze.exit and a == maze.exit_outside:
        return True

    ax, ay = a
    bx, by = b
    if not (0 <= ax < SIZE and 0 <= ay < SIZE and 0 <= bx < SIZE and 0 <= by < SIZE):
        return False
    if ax == bx and abs(ay - by) == 1:
        return not maze.h_walls[max(ay, by)][ax]
    if ay == by and abs(ax - bx) == 1:
        return not maze.v_walls[ay][max(ax, bx)]
    return False


def count_routes(maze: Maze, limit: int) -> int:
    count = 0
    seen = {maze.entrance}

    def dfs(pos: tuple[int, int]) -> None:
        nonlocal count
        if count >= limit:
            return
        if pos == maze.exit:
            count += 1
            return
        for nxt in neighbors(maze, pos):
            if nxt in (maze.start_outside, maze.exit_outside) or nxt in seen:
                continue
            seen.add(nxt)
            dfs(nxt)
            seen.remove(nxt)

    dfs(maze.entrance)
    return count


def shortest_cell_path(maze: Maze) -> list[tuple[int, int]]:
    queue = [maze.entrance]
    prev = {maze.entrance: None}

    for pos in queue:
        if pos == maze.exit:
            break
        for nxt in neighbors(maze, pos):
            if nxt in (maze.start_outside, maze.exit_outside) or nxt in prev:
                continue
            prev[nxt] = pos
            queue.append(nxt)

    path = []
    pos = maze.exit
    while pos is not None:
        path.append(pos)
        pos = prev[pos]
    return list(reversed(path))


def solve_optimal(maze: Maze) -> tuple[int, int]:
    dist = {maze.start_outside: 0}
    paths = {maze.start_outside: 1}
    heap = [(0, maze.start_outside)]

    while heap:
        cost, pos = heapq.heappop(heap)
        if cost != dist[pos]:
            continue
        for nxt in neighbors(maze, pos):
            new_cost = cost + step_cost(maze, nxt)
            if new_cost < dist.get(nxt, 10**9):
                dist[nxt] = new_cost
                paths[nxt] = paths[pos]
                heapq.heappush(heap, (new_cost, nxt))
            elif new_cost == dist.get(nxt):
                paths[nxt] += paths[pos]

    return dist.get(maze.exit_outside, 10**9), paths.get(maze.exit_outside, 0)


def score_answer(maze: Maze, answer: str) -> tuple[bool, int, str]:
    pos = maze.start_outside
    score = 0
    entered_maze = False
    directions = {
        "L": (-1, 0),
        "R": (1, 0),
        "U": (0, -1),
        "D": (0, 1),
    }

    for char in answer:
        if char not in directions:
            return False, score, f"bad input character: {char!r}"
        dx, dy = directions[char]
        nxt = (pos[0] + dx, pos[1] + dy)
        if not passable(maze, nxt) or not open_between(maze, pos, nxt):
            if not entered_maze and pos == maze.start_outside:
                return False, score, "You did not enter the maze"
            return False, score, "You hit a wall"
        score += step_cost(maze, nxt)
        pos = nxt
        if 0 <= pos[0] < SIZE and 0 <= pos[1] < SIZE:
            entered_maze = True
        if pos == maze.exit_outside:
            break

    if pos != maze.exit_outside:
        if pos == maze.start_outside:
            if entered_maze:
                return False, score, "You left the start of the maze"
            return False, score, "You did not enter the maze"
        return False, score, "You did not reach the exit"
    return score == maze.optimal_score, score, "not the least-point path"


def generate_pow_challenge(difficulty: int) -> str:
    d_bytes = struct.pack(">I", difficulty)
    x = int.from_bytes(secrets.token_bytes(16), "big")
    return f"s.{b64(d_bytes)}.{b64(int_to_bytes(x))}"


def check_pow_solution(challenge: str, solution: str) -> bool:
    try:
        c_version, d_part, x_part = challenge.split(".", 2)
        s_version, y_part = solution.split(".", 1)
        if c_version != "s" or s_version != "s":
            return False
        d_bytes = base64.b64decode(d_part, validate=True)
        if len(d_bytes) > 4:
            return False
        difficulty = int.from_bytes(d_bytes.rjust(4, b"\x00"), "big")
        x = int.from_bytes(base64.b64decode(x_part, validate=True), "big")
        y = int.from_bytes(base64.b64decode(y_part, validate=True), "big")
    except (ValueError, binascii.Error):
        return False

    for _ in range(difficulty):
        y ^= 1
        y = pow(y, 2, POW_MOD)
    return y == x or y == POW_MOD - x


def b64(data: bytes) -> str:
    return base64.b64encode(data).decode("ascii")


def int_to_bytes(value: int) -> bytes:
    if value == 0:
        return b""
    return value.to_bytes((value.bit_length() + 7) // 8, "big")


class MazeHandler(socketserver.StreamRequestHandler):
    def handle(self) -> None:
        try:
            self.run_session()
        except (BrokenPipeError, ConnectionResetError):
            return

    def run_session(self) -> None:
        self.request.settimeout(None)
        if not self.run_pow():
            return
        self.send(read_banner())
        self.run_menu()

    def run_pow(self) -> bool:
        if POW_DIFFICULTY <= 0:
            return True
        challenge = generate_pow_challenge(POW_DIFFICULTY)
        self.send(f"proof of work: curl -sSfL https://pwn.red/pow | sh -s {challenge}\n")
        self.send("solution: ")
        raw = self.rfile.readline(4096)
        if not raw:
            return False
        solution = raw.decode("utf-8", "ignore").strip()
        if not check_pow_solution(challenge, solution):
            self.send("bad\n")
            return False
        self.send("good\n\n")
        return True

    def run_menu(self) -> None:
        while True:
            self.send_menu()
            raw = self.rfile.readline(4096)
            if not raw:
                return
            choice = raw.decode("utf-8", "ignore").strip()
            if choice == "1":
                info = read_info()
                self.send(info)
                if not info.endswith("\n"):
                    self.send("\n")
                self.send("\n")
            elif choice == "2":
                self.run_rounds()
                return
            elif choice == "3":
                self.send("bye\n")
                return
            else:
                self.send("Invalid option.\n\n")

    def send_menu(self) -> None:
        self.send("1. Info about this challenge\n")
        self.send("2. Begin\n")
        self.send("3. Exit\n")
        self.send("> ")

    def run_rounds(self) -> None:
        self.send("Maze Captcha\n")
        self.send("Submit only L/R/U/D characters, with no spaces.\n\n")

        for round_no in range(1, ROUNDS + 1):
            maze = make_maze()
            self.send(render(maze, round_no))
            start = time.monotonic()
            self.request.settimeout(ROUND_SECONDS)

            try:
                raw = self.rfile.readline(4096)
            except TimeoutError:
                self.send("\nToo slow.\n")
                return
            except OSError:
                return
            finally:
                with contextlib.suppress(OSError):
                    self.request.settimeout(None)

            if time.monotonic() - start > ROUND_SECONDS:
                self.send("\nToo slow.\n")
                return
            if not raw:
                return

            answer = raw.decode("utf-8", "ignore").strip().upper()
            ok, score, reason = score_answer(maze, answer)
            if not ok:
                self.send(f"\nWrong. Score: {score}. Optimal: {maze.optimal_score}. {reason}.\n")
                return
            self.send(f"\nCorrect. Score: {score}.\n\n")

        self.send(read_flag())

    def send(self, data: str) -> None:
        self.wfile.write(data.encode("utf-8"))
        self.wfile.flush()


class ThreadedTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    allow_reuse_address = True
    daemon_threads = True


def read_flag() -> str:
    try:
        with open(os.path.join(BASE_DIR, "flag.txt"), "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return "flag{missing_flag_file}"


def read_info() -> str:
    return "\n".join(
        [
            "Maze Captcha",
            "",
            "Are you a clanker?! To prove that you aren\'t some filthy AI bot, this challenge requires you to solve 100 rounds of a maze captcha. But it\'s not just any regular maze - each maze is 11x11 tiles, and contains emojis of various board game pieces, each with its own weight. Why? Because even though LLMs are apparently sooo smart, they are lonely and have no friends and no one likes them so they have never been invited to game night before.",
            "",
            "The player starts before the green entrance wall. Their goal is to pass the red exit wall with the least amount of points. Players accumulate points in two ways. Each movement from one tile to the next adds 1 point, and any emojis the player walks through will add additional points. These additional points are as follows.",
            "",
            format_table("Chess", CHESS_INFO_ROWS),
            "",
            format_table("Cards", CARD_INFO_ROWS),
            "",
            format_table("Dice", DICE_INFO_ROWS),
            "",
            format_table("Dominoes", DOMINO_INFO_ROWS),
            "",
            format_table("Mahjong", MAHJONG_INFO_ROWS),
            "",
            'Each round lasts 5 seconds, and your path through the maze can be entered as a string containing "L", "R", "U", or "D". These letters represent left, right, up, and down respectively.',
            "",
            "There will always be a unique minimal path. After 100 successful rounds, the flag will be printed. Good luck!",
            "",
        ]
    )


def read_banner() -> str:
    try:
        with open(os.path.join(BASE_DIR, "banner.txt"), "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return ""


def format_table(title: str, rows: list[tuple[str, int]]) -> str:
    emoji_width = max(display_width("Emoji"), *(display_width(row[0]) for row in rows))
    points_width = max(display_width("Points"), *(len(str(row[1])) for row in rows))
    border = f"+-{'-' * emoji_width}-+-{'-' * points_width}-+"
    lines = [
        title,
        border,
        f"| {'Emoji'.ljust(emoji_width)} | {'Points'.rjust(points_width)} |",
        border,
    ]
    for emoji, points in rows:
        lines.append(f"| {pad_display(emoji, emoji_width)} | {str(points).rjust(points_width)} |")
    lines.append(border)
    return "\n".join(lines)


def pad_display(text: str, width: int) -> str:
    return text + " " * max(0, width - display_width(text))


CHESS_INFO_ROWS = [
    ("♙", 1),
    ("♘", 3),
    ("♗", 3),
    ("♖", 5),
    ("♕", 9),
    ("♔", 100),
]

CARD_INFO_ROWS = [
    ("🂡, 🂱, 🃑, 🃁", 1),
    ("🂢, 🂲, 🃒, 🃂", 2),
    ("🂣, 🂳, 🃓, 🃃", 3),
    ("🂤, 🂴, 🃔, 🃄", 4),
    ("🂥, 🂵, 🃕, 🃅", 5),
    ("🂦, 🂶, 🃖, 🃆", 6),
    ("🂧, 🂷, 🃗, 🃇", 7),
    ("🂨, 🂸, 🃘, 🃈", 8),
    ("🂩, 🂹, 🃙, 🃉", 9),
    ("🂪, 🂺, 🃚, 🃊", 10),
    ("🂫, 🂻, 🃛, 🃋", 10),
    ("🂭, 🂽, 🃝, 🃍", 10),
    ("🂮, 🂾, 🃞, 🃎", 10),
]

DICE_INFO_ROWS = [
    ("⚀", 1),
    ("⚁", 2),
    ("⚂", 3),
    ("⚃", 4),
    ("⚄", 5),
    ("⚅", 6),
]

DOMINO_INFO_ROWS = [
    ("🁣", 0),
    ("🁤, 🁪", 1),
    ("🁥, 🁫, 🁱", 2),
    ("🁦, 🁬, 🁲, 🁸", 3),
    ("🁧, 🁭, 🁳, 🁹, 🁿", 4),
    ("🁨, 🁮, 🁴, 🁺, 🂀, 🂆", 5),
    ("🁩, 🁯, 🁵, 🁻, 🂁, 🂇, 🂍", 6),
    ("🁰, 🁶, 🁼, 🂂, 🂈, 🂎", 7),
    ("🁷, 🁽, 🂃, 🂉, 🂏", 8),
    ("🁾, 🂄, 🂊, 🂐", 9),
    ("🂅, 🂋, 🂑", 10),
    ("🂌, 🂒", 11),
    ("🂓", 12),
]

MAHJONG_INFO_ROWS = [
    ("🀇, 🀐, 🀙", 1),
    ("🀈, 🀑, 🀚", 2),
    ("🀉, 🀒, 🀛", 3),
    ("🀊, 🀓, 🀜", 4),
    ("🀋, 🀔, 🀝", 5),
    ("🀌, 🀕, 🀞", 6),
    ("🀍, 🀖, 🀟", 7),
    ("🀎, 🀗, 🀠", 8),
    ("🀏, 🀘, 🀡", 9),
]


def main() -> None:
    with ThreadedTCPServer((HOST, PORT), MazeHandler) as server:
        print(f"listening on {HOST}:{PORT}")
        server.serve_forever()


if __name__ == "__main__":
    main()
