const check = document.getElementById("check");
const captcha = document.getElementById("captcha");
const mazeEl = document.getElementById("maze");
const roundEl = document.getElementById("round");
const timerEl = document.getElementById("timer");
const statusEl = document.getElementById("status");
const tryAgain = document.getElementById("try-again");
const success = document.getElementById("success");
const flagEl = document.getElementById("flag");

let round = null;
let current = null;
let path = [];
let deadline = 0;
let timerId = 0;
let failed = false;
let submitting = false;
let cellPx = 44;

check.addEventListener("click", start);
tryAgain.addEventListener("click", resetScreen);
document.addEventListener("keydown", handleKeyDown);

async function start() {
  statusEl.textContent = "";
  tryAgain.classList.add("hidden");
  success.classList.add("hidden");
  flagEl.textContent = "";
  const res = await fetch("/api/start", { method: "POST" });
  round = await res.json();
  check.classList.add("hidden");
  captcha.classList.remove("hidden");
  renderRound();
}

function renderRound() {
  current = [...round.entrance];
  path = [[...current]];
  failed = false;
  submitting = false;
  statusEl.textContent = "";
  tryAgain.classList.add("hidden");
  mazeEl.replaceChildren();
  configureMazeLayout();
  captcha.classList.toggle(
    "bottom-outside",
    round.start[1] === round.size || round.exitOutside[1] === round.size,
  );
  roundEl.textContent = `Round ${round.round}/${round.rounds}`;
  deadline = performance.now() + round.seconds * 1000;
  clearInterval(timerId);
  timerId = setInterval(updateTimer, 50);
  updateTimer();

  for (let y = 0; y < round.size; y++) {
    for (let x = 0; x < round.size; x++) {
      const tile = document.createElement("div");
      tile.className = "tile";
      tile.dataset.x = x;
      tile.dataset.y = y;
      const img = document.createElement("img");
      img.src = round.tiles[y][x];
      img.alt = "";
      tile.appendChild(img);
      mazeEl.appendChild(tile);
    }
  }
  addWalls();
  addOutsideDot("start-dot", round.start);
  addOutsideDot("exit-dot", round.exitOutside);
  document.querySelector(".start-dot")?.classList.add("visited");
  renderPosition();
}

function configureMazeLayout() {
  const angle = (round.rotation * Math.PI) / 180;
  const visualCells = round.size + 2;
  const rotatedCells = visualCells * (Math.abs(Math.cos(angle)) + Math.abs(Math.sin(angle)));
  const availableWidth = Math.max(320, window.innerWidth - 48);
  const availableHeight = Math.max(320, window.innerHeight - 150);
  cellPx = Math.max(22, Math.min(round.cell, Math.floor(Math.min(availableWidth, availableHeight) / rotatedCells)));
  const boardPx = round.size * cellPx;
  const rotatedVisualPx = Math.ceil(rotatedCells * cellPx);
  const marginPx = Math.max(cellPx, Math.ceil((rotatedVisualPx - boardPx) / 2));
  captcha.style.setProperty("--cell", `${cellPx}px`);
  mazeEl.style.setProperty("--maze-margin", `${marginPx}px`);
  mazeEl.style.setProperty("--maze-rotation", `${round.rotation}deg`);
}

function addWalls() {
  for (let y = 0; y <= round.size; y++) {
    for (let x = 0; x < round.size; x++) {
      if (round.hWalls[y][x]) addWall("h", x, y);
    }
  }
  for (let y = 0; y < round.size; y++) {
    for (let x = 0; x <= round.size; x++) {
      if (round.vWalls[y][x]) addWall("v", x, y);
    }
  }
}

function addWall(kind, x, y) {
  const wall = document.createElement("div");
  wall.className = `wall ${kind}`;
  wall.style.left = `${x * cellPx}px`;
  wall.style.top = `${y * cellPx}px`;
  mazeEl.appendChild(wall);
}

function updateTimer() {
  const left = Math.max(0, (deadline - performance.now()) / 1000);
  timerEl.textContent = left.toFixed(1);
  if (left <= 0) failRound("Captcha failed. You ran out of time!");
}

function addOutsideDot(className, outside) {
  const dot = document.createElement("div");
  dot.className = `outside-dot ${className}`;
  const [x, y] = outside;
  dot.style.left = `${x * cellPx + cellPx / 2}px`;
  dot.style.top = `${y * cellPx + cellPx / 2}px`;
  mazeEl.appendChild(dot);
}

function handleKeyDown(event) {
  if (!round || failed || submitting) return;
  const movement = keyMovement(event.key);
  if (!movement) return;
  event.preventDefault();
  void movePlayer(movement[0], movement[1]);
}

function keyMovement(key) {
  const normalized = key.toLowerCase();
  const forward = entranceDirection();
  const left = [forward[1], -forward[0]];
  const right = [-forward[1], forward[0]];
  if (normalized === "arrowup" || normalized === "w") return forward;
  if (normalized === "arrowdown" || normalized === "s") return [-forward[0], -forward[1]];
  if (normalized === "arrowleft" || normalized === "a") return left;
  if (normalized === "arrowright" || normalized === "d") return right;
  return null;
}

function entranceDirection() {
  return [round.entrance[0] - round.start[0], round.entrance[1] - round.start[1]];
}

async function movePlayer(dx, dy) {
  const [x, y] = current;
  const next = [x + dx, y + dy];
  if (!inBounds(next) || !openBetween(x, y, next[0], next[1])) return;
  submitting = true;
  const res = await fetch("/api/move", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ position: next, submitToken: round.submitToken }),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    failRound(data.message || "Captcha failed.");
    return;
  }
  if (data.done) {
    clearInterval(timerId);
    showSuccess(data.flag);
    return;
  }
  if (data.next) {
    round = data.next;
    renderRound();
    return;
  }
  current = next;
  path.push([...current]);
  renderPosition();
  submitting = false;
}

function inBounds(tile) {
  return tile[0] >= 0 && tile[0] < round.size && tile[1] >= 0 && tile[1] < round.size;
}

function renderPosition() {
  document.querySelector(".tile.current")?.classList.remove("current");
  const tile = tileElement(current[0], current[1]);
  tile?.classList.add("visited", "current");
}

function tileElement(x, y) {
  return mazeEl.querySelector(`.tile[data-x="${x}"][data-y="${y}"]`);
}

function openBetween(ax, ay, bx, by) {
  if (ax === bx && Math.abs(ay - by) === 1) return !round.hWalls[Math.max(ay, by)][ax];
  if (ay === by && Math.abs(ax - bx) === 1) return !round.vWalls[ay][Math.max(ax, bx)];
  return false;
}

function failRound(message) {
  if (failed) return;
  failed = true;
  submitting = false;
  clearInterval(timerId);
  statusEl.textContent = message;
  captcha.classList.remove("hidden");
  check.classList.add("hidden");
  tryAgain.classList.remove("hidden");
}

function resetScreen() {
  clearInterval(timerId);
  failed = false;
  submitting = false;
  round = null;
  current = null;
  path = [];
  statusEl.textContent = "";
  mazeEl.replaceChildren();
  captcha.style.removeProperty("--cell");
  mazeEl.style.removeProperty("--maze-margin");
  mazeEl.style.removeProperty("--maze-rotation");
  captcha.classList.remove("bottom-outside");
  tryAgain.classList.add("hidden");
  captcha.classList.add("hidden");
  check.classList.remove("hidden");
}

function showSuccess(flag) {
  round = null;
  captcha.classList.add("hidden");
  check.classList.add("hidden");
  mazeEl.replaceChildren();
  success.classList.remove("hidden");
  flagEl.textContent = "";
  const box = success.querySelector(".animated-box");
  box.classList.remove("play");
  void box.offsetWidth;
  box.classList.add("play");
  window.setTimeout(() => {
    flagEl.textContent = flag;
    flagEl.classList.add("visible");
  }, 850);
}
