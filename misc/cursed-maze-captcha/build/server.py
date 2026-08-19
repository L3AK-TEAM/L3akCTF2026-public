import io
import math
import os
import random
import secrets
import threading
import time
from pathlib import Path
from flask import Flask, abort, jsonify, make_response, request, send_file, send_from_directory
from PIL import Image

class Maze:
    def __init__(self, horizontal_walls, vertical_walls, start, outside_exit,
                 entrance, exit_tile, background, rotation):
        self.horizontal_walls = horizontal_walls
        self.vertical_walls = vertical_walls
        self.start = start
        self.outside_exit = outside_exit
        self.entrance = entrance
        self.exit = exit_tile
        self.path = []
        self.background = background
        self.rotation = rotation

base_dir = os.path.dirname(os.path.abspath(__file__))
host = os.environ.get("HOST", "0.0.0.0")
port = int(os.environ.get("PORT", "1337"))
size = 11
rounds = 100
round_seconds = 20
cell_px = 44
top_marker_columns = tuple(range(2, size - 2))

app = Flask(__name__, static_folder=None)
app.config["MAX_CONTENT_LENGTH"] = 4096
sessions = {}
tile_cache = {}
sessions_lock = threading.Lock()

def make_maze():
    while True:
        maze = make_candidate()
        route_count = count_routes(maze, 9)
        path, shortest_count = find_shortest_path(maze)

        if 4 <= route_count <= 8 and shortest_count == 1 and starts_inward(maze, path):
            maze.path = path
            return maze

def make_candidate():
    horizontal_walls = [[True for _ in range(size)] for _ in range(size + 1)]
    vertical_walls = [[True for _ in range(size + 1)] for _ in range(size)]

    carve_maze(horizontal_walls, vertical_walls)
    open_extra_walls(horizontal_walls, vertical_walls, random.randint(1, 5))

    side = random.choice(("left", "right", "top", "bottom"))

    if side in ("left", "right"):
        start_y = random.randrange(size)
        exit_y = random.randrange(size)

        if side == "left":
            entrance = (0, start_y)
            exit_tile = (size - 1, exit_y)
            start = (-1, start_y)
            outside_exit = (size, exit_y)
            vertical_walls[start_y][0] = False
            vertical_walls[exit_y][size] = False
        else:
            entrance = (size - 1, start_y)
            exit_tile = (0, exit_y)
            start = (size, start_y)
            outside_exit = (-1, exit_y)
            vertical_walls[start_y][size] = False
            vertical_walls[exit_y][0] = False
    else:
        if side == "top":
            start_x = random.choice(top_marker_columns)
            exit_x = random.randrange(size)
            entrance = (start_x, 0)
            exit_tile = (exit_x, size - 1)
            start = (start_x, -1)
            outside_exit = (exit_x, size)
            horizontal_walls[0][start_x] = False
            horizontal_walls[size][exit_x] = False
        else:
            start_x = random.randrange(size)
            exit_x = random.choice(top_marker_columns)
            entrance = (start_x, size - 1)
            exit_tile = (exit_x, 0)
            start = (start_x, size)
            outside_exit = (exit_x, -1)
            horizontal_walls[size][start_x] = False
            horizontal_walls[0][exit_x] = False

    return Maze(
        horizontal_walls,
        vertical_walls,
        start,
        outside_exit,
        entrance,
        exit_tile,
        make_background(),
        random.uniform(0, 360)
    )

def make_background():
    colors = []
    base_hue = random.random()
    offsets = (
        0,
        random.uniform(0.18, 0.38),
        random.uniform(0.55, 0.78),
        random.uniform(0.82, 0.96)
    )

    for offset in offsets:
        hue = (base_hue + offset) % 1
        colors.append(hsv_rgb(
            hue,
            random.uniform(0.42, 0.78),
            random.uniform(0.76, 0.98)
        ))

    return {
        "angle": random.uniform(0, math.tau),
        "colors": tuple(colors),
        "wave_angle": random.uniform(0, math.tau),
        "wave_frequency": random.uniform(2, 4.6),
        "wave_phase": random.uniform(0, math.tau),
        "wave_strength": random.uniform(0.05, 0.12)
    }

def hsv_rgb(hue, saturation, value):
    chroma = value * saturation
    hue *= 6
    x = chroma * (1 - abs(hue % 2 - 1))

    if hue < 1:
        rgb = (chroma, x, 0)
    elif hue < 2:
        rgb = (x, chroma, 0)
    elif hue < 3:
        rgb = (0, chroma, x)
    elif hue < 4:
        rgb = (0, x, chroma)
    elif hue < 5:
        rgb = (x, 0, chroma)
    else:
        rgb = (chroma, 0, x)

    adjustment = value - chroma
    return tuple(round((channel + adjustment) * 255) for channel in rgb)

def carve_maze(horizontal_walls, vertical_walls):
    start = (random.randrange(size), random.randrange(size))
    visited = {start}
    stack = [start]

    while stack:
        current = stack[-1]
        choices = [neighbor for neighbor in cell_neighbors(current) if neighbor not in visited]

        if not choices:
            stack.pop()
            continue

        next_cell = random.choice(choices)
        remove_wall(horizontal_walls, vertical_walls, current, next_cell)
        visited.add(next_cell)
        stack.append(next_cell)

def open_extra_walls(horizontal_walls, vertical_walls, count):
    choices = []

    for y in range(size):
        for x in range(size):
            if x + 1 < size and vertical_walls[y][x + 1]:
                choices.append(((x, y), (x + 1, y)))
            if y + 1 < size and horizontal_walls[y + 1][x]:
                choices.append(((x, y), (x, y + 1)))

    random.shuffle(choices)
    for a, b in choices[:count]:
        remove_wall(horizontal_walls, vertical_walls, a, b)

def remove_wall(horizontal_walls, vertical_walls, a, b):
    ax, ay = a
    bx, by = b

    if ax == bx:
        horizontal_walls[max(ay, by)][ax] = False
    else:
        vertical_walls[ay][max(ax, bx)] = False

def cell_neighbors(position):
    x, y = position

    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        next_x = x + dx
        next_y = y + dy
        if 0 <= next_x < size and 0 <= next_y < size:
            yield next_x, next_y

def neighbors(maze, position):
    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        next_position = (position[0] + dx, position[1] + dy)
        x, y = next_position
        inside = 0 <= x < size and 0 <= y < size

        if (inside or next_position in (maze.start, maze.outside_exit)) and open_between(maze, position, next_position):
            yield next_position

def open_between(maze, a, b):
    if {a, b} == {maze.start, maze.entrance}:
        return True
    if {a, b} == {maze.exit, maze.outside_exit}:
        return True

    ax, ay = a
    bx, by = b

    if not (0 <= ax < size and 0 <= ay < size and 0 <= bx < size and 0 <= by < size):
        return False
    if ax == bx and abs(ay - by) == 1:
        return not maze.horizontal_walls[max(ay, by)][ax]
    if ay == by and abs(ax - bx) == 1:
        return not maze.vertical_walls[ay][max(ax, bx)]
    return False

def count_routes(maze, limit):
    count = 0
    seen = {maze.entrance}

    def search(position):
        nonlocal count

        if count >= limit:
            return
        if position == maze.exit:
            count += 1
            return

        for next_position in neighbors(maze, position):
            if next_position in (maze.start, maze.outside_exit) or next_position in seen:
                continue
            seen.add(next_position)
            search(next_position)
            seen.remove(next_position)

    search(maze.entrance)
    return count

def find_shortest_path(maze):
    queue = [maze.entrance]
    previous = {maze.entrance: None}
    distances = {maze.entrance: 0}
    path_counts = {maze.entrance: 1}

    for position in queue:
        for next_position in neighbors(maze, position):
            if next_position in (maze.start, maze.outside_exit):
                continue

            distance = distances[position] + 1
            if next_position not in distances:
                distances[next_position] = distance
                previous[next_position] = position
                path_counts[next_position] = path_counts[position]
                queue.append(next_position)
            elif distances[next_position] == distance:
                path_counts[next_position] += path_counts[position]

    if maze.exit not in distances:
        return [], 0

    path = []
    position = maze.exit
    while position is not None:
        path.append(position)
        position = previous[position]

    return list(reversed(path)), path_counts[maze.exit]

def starts_inward(maze, path):
    if len(path) < 2:
        return False

    dx = maze.entrance[0] - maze.start[0]
    dy = maze.entrance[1] - maze.start[1]
    return path[1] == (maze.entrance[0] + dx, maze.entrance[1] + dy)

def get_session(create=False):
    session_id = request.cookies.get("maze_session", "")

    with sessions_lock:
        data = sessions.get(session_id)
        if data:
            return session_id, data
        if not create:
            return "", None

        session_id = secrets.token_urlsafe(32)
        data = {
            "round": 0,
            "maze": None,
            "token": "",
            "started": 0,
            "progress": 0,
            "failed": False,
            "last_seen": time.monotonic(),
            "lock": threading.Lock()
        }
        sessions[session_id] = data
        return session_id, data

def cleanup_sessions():
    now = time.monotonic()

    with sessions_lock:
        old_sessions = [
            session_id
            for session_id, data in sessions.items()
            if now - data.get("last_seen", now) > 900
        ]

        for session_id in old_sessions:
            sessions.pop(session_id, None)
            clear_tile_cache(session_id)

def round_data(session_id, data):
    maze = data["maze"]
    token = data["token"]

    return {
        "round": data["round"],
        "rounds": rounds,
        "seconds": round_seconds,
        "size": size,
        "cell": cell_px,
        "hWalls": maze.horizontal_walls,
        "vWalls": maze.vertical_walls,
        "start": maze.start,
        "entrance": maze.entrance,
        "exit": maze.exit,
        "exitOutside": maze.outside_exit,
        "rotation": maze.rotation,
        "submitToken": token,
        "tiles": [
            [f"/tile/{session_id}/{token}/({x},{y}).png" for x in range(size)]
            for y in range(size)
        ]
    }

def start_round(session_id, data):
    clear_tile_cache(session_id)
    data["round"] += 1
    data["maze"] = make_maze()
    data["token"] = secrets.token_urlsafe(24)
    data["started"] = time.monotonic()
    data["progress"] = 0
    data["last_seen"] = time.monotonic()

@app.after_request
def set_security_headers(response):
    response.headers["Content-Security-Policy"] = "default-src 'self'; img-src 'self'; style-src 'self'; script-src 'self'; base-uri 'none'; frame-ancestors 'none'"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Cache-Control"] = "no-store"
    return response

@app.get("/")
def index():
    return send_from_directory(os.path.join(base_dir, "static"), "index.html")

@app.get("/static/app.js")
def static_app_js():
    return send_from_directory(os.path.join(base_dir, "static"), "app.js")

@app.get("/static/style.css")
def static_style_css():
    return send_from_directory(os.path.join(base_dir, "static"), "style.css")

@app.post("/api/start")
def api_start():
    cleanup_sessions()
    session_id, data = get_session(True)

    with data["lock"]:
        lock = data["lock"]
        data.clear()
        data.update({
            "round": 0,
            "maze": None,
            "token": "",
            "started": 0,
            "progress": 0,
            "failed": False,
            "last_seen": time.monotonic(),
            "lock": lock
        })
        start_round(session_id, data)

    response = make_response(jsonify(round_data(session_id, data)))
    response.set_cookie(
        "maze_session",
        session_id,
        httponly=True,
        secure=False,
        samesite="Strict",
        max_age=900
    )
    return response

@app.post("/api/move")
def api_move():
    session_id, data = get_session()

    if not data or data.get("failed") or not data.get("maze"):
        abort(400)

    with data["lock"]:
        if data.get("failed") or not data.get("maze"):
            abort(400)

        data["last_seen"] = time.monotonic()

        if time.monotonic() - data["started"] > round_seconds:
            data["failed"] = True
            return jsonify({"ok": False, "message": "Captcha failed. You ran out of time!"}), 400

        body = request.get_json(silent=True) or {}
        if body.get("submitToken") != data["token"]:
            abort(400)

        position = body.get("position")
        if not isinstance(position, list) or len(position) != 2:
            abort(400)
        if not isinstance(position[0], int) or not isinstance(position[1], int):
            abort(400)

        maze = data["maze"]
        next_index = data["progress"] + 1
        expected = maze.path[next_index] if next_index < len(maze.path) else None
        position = tuple(position)

        if position != expected:
            data["failed"] = True
            return jsonify({
                "ok": False,
                "message": "Wrong. You left the shortest path. Click again to retry from round 1."
            }), 400

        data["progress"] = next_index

        if position != maze.exit:
            return jsonify({"ok": True, "done": False, "position": list(position)})

        if data["round"] >= rounds:
            try:
                flag = (Path(base_dir) / "flag.txt").read_text(encoding="utf-8").strip()
            except FileNotFoundError:
                flag = "flag{missing_flag_file}"

            with sessions_lock:
                sessions.pop(session_id, None)
            clear_tile_cache(session_id)
            return jsonify({"ok": True, "done": True, "flag": flag})

        start_round(session_id, data)
        return jsonify({
            "ok": True,
            "done": False,
            "next": round_data(session_id, data)
        })

@app.get("/tile/<session_id>/<token>/(<int:x>,<int:y>).png")
def tile(session_id, token, x, y):
    data = sessions.get(session_id)

    if not data or data.get("token") != token or not (0 <= x < size and 0 <= y < size):
        abort(404)

    cache_key = (session_id, token, x, y)
    if cache_key not in tile_cache:
        if Image is None:
            abort(500)
        image = render_background_tile(data["maze"].background, x, y)
        output = io.BytesIO()
        image.save(output, format="PNG", compress_level=0, optimize=False)
        tile_cache[cache_key] = output.getvalue()

    return send_file(io.BytesIO(tile_cache[cache_key]), mimetype="image/png", max_age=0)

def clear_tile_cache(session_id):
    for key in list(tile_cache):
        if key[0] == session_id:
            tile_cache.pop(key, None)

def render_background_tile(background, tile_x, tile_y):
    image = Image.new("RGBA", (cell_px, cell_px), (255, 255, 255, 255))
    pixels = image.load()
    direction_x = math.cos(background["angle"])
    direction_y = math.sin(background["angle"])
    wave_x = math.cos(background["wave_angle"])
    wave_y = math.sin(background["wave_angle"])
    projection_max = max(0.001, (abs(direction_x) + abs(direction_y)) / 2)

    width = size * cell_px
    height = size * cell_px

    for local_y in range(cell_px):
        y = (tile_y * cell_px + local_y) / (height - 1) - 0.5

        for local_x in range(cell_px):
            x = (tile_x * cell_px + local_x) / (width - 1) - 0.5
            progress = (x * direction_x + y * direction_y) / projection_max / 2 + 0.5
            wave = math.sin(
                (x * wave_x + y * wave_y) * background["wave_frequency"] * math.tau
                + background["wave_phase"]
            )
            progress = max(0, min(1, progress + wave * background["wave_strength"]))
            red, green, blue = gradient_color(background["colors"], progress)
            pixels[local_x, local_y] = (red, green, blue, 255)

    return image

def gradient_color(colors, progress):
    scaled = progress * (len(colors) - 1)
    index = min(len(colors) - 2, int(scaled))
    blend = scaled - index
    left = colors[index]
    right = colors[index + 1]

    return tuple(
        round(left[channel] + (right[channel] - left[channel]) * blend)
        for channel in range(3)
    )

if __name__ == "__main__":
    app.run(host=host, port=port, threaded=True)
