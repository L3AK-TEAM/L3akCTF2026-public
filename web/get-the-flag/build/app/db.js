const Database = require("better-sqlite3");
const bcrypt = require("bcryptjs");
const crypto = require("crypto");

const db = new Database("/tmp/ctf.db");

db.pragma("journal_mode = WAL");

db.exec(`
  CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'user'
  )
`);

const ADMIN_PASSWORD = crypto.randomBytes(32).toString("hex");
const hash = bcrypt.hashSync(ADMIN_PASSWORD, 10);

const existing = db.prepare("SELECT id FROM users WHERE username = ?").get("admin");
if (!existing) {
  db.prepare("INSERT INTO users (username, password, role) VALUES (?, ?, ?)").run("admin", hash, "admin");
}

function createUser(username, password) {
  const hashed = bcrypt.hashSync(password, 10);
  return db.prepare("INSERT INTO users (username, password, role) VALUES (?, ?, 'user')").run(username, hashed);
}

function findUserByUsername(username) {
  return db.prepare("SELECT * FROM users WHERE username = ?").get(username);
}

function findUserById(id) {
  return db.prepare("SELECT * FROM users WHERE id = ?").get(id);
}

function verifyPassword(plaintext, hashed) {
  return bcrypt.compareSync(plaintext, hashed);
}

function changePassword(userId, newPassword) {
  const hashed = bcrypt.hashSync(newPassword, 10);
  db.prepare("UPDATE users SET password = ? WHERE id = ?").run(hashed, userId);
}

module.exports = {
  ADMIN_PASSWORD,
  createUser,
  findUserByUsername,
  findUserById,
  verifyPassword,
  changePassword,
};
