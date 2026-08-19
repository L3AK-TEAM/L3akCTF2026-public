const express = require("express");
const session = require("express-session");
const methodOverride = require("method-override");
const crypto = require("crypto");
const path = require("path");
const fs = require("fs");
const { v4: uuidv4 } = require("uuid");

const {
  createUser,
  findUserByUsername,
  findUserById,
  verifyPassword,
  changePassword,
} = require("./db");
const { visitPage } = require("./bot");

const app = express();
const FLAG = process.env.FLAG || "L3AK{FAKE_FLAG_FOR_TESTING}";
const PAGES_DIR = path.join(__dirname, "uploads");

app.set("view engine", "ejs");
app.set("views", path.join(__dirname, "views"));

fs.mkdirSync(PAGES_DIR, { recursive: true });

app.use(express.urlencoded({ extended: false }));

app.use(
  methodOverride((req) => {
    if (typeof req.query._method === "string") {
      return req.query._method.toUpperCase();
    }
  })
);

app.use(
  session({
    secret: process.env.SESSION_SECRET || crypto.randomBytes(32).toString("hex"),
    resave: false,
    saveUninitialized: false,
    cookie: {
      httpOnly: true,
      sameSite: "lax",
    },
  })
);

app.use((req, res, next) => {
  if (req.session.userId && !req.session.csrf) {
    req.session.csrf = crypto.randomBytes(32).toString("hex");
  }
  next();
});

function requireLogin(req, res, next) {
  if (!req.session.userId) {
    return res.redirect("/login");
  }
  next();
}

function csrfOnPostOnly(req, res, next) {
  if (req.method !== "POST") {
    return next();
  }

  if (!req.body.csrf || req.body.csrf !== req.session.csrf) {
    return res.status(403).send("Invalid CSRF token");
  }

  next();
}

app.get("/", (req, res) => {
  if (req.session.userId) return res.redirect("/dashboard");
  res.redirect("/login");
});

app.get("/login", (req, res) => {
  if (req.session.userId) return res.redirect("/dashboard");
  res.render("login", { error: null });
});

app.post("/login", (req, res) => {
  const { username, password } = req.body;

  if (!username || !password) {
    return res.render("login", { error: "Username and password are required" });
  }

  const user = findUserByUsername(username);
  if (!user || !verifyPassword(password, user.password)) {
    return res.render("login", { error: "Invalid credentials" });
  }

  req.session.userId = user.id;
  req.session.username = user.username;
  req.session.csrf = crypto.randomBytes(32).toString("hex");
  res.redirect("/dashboard");
});

app.get("/register", (req, res) => {
  if (req.session.userId) return res.redirect("/dashboard");
  res.render("register", { error: null });
});

app.post("/register", (req, res) => {
  const { username, password, confirm } = req.body;

  if (!username || !password || !confirm) {
    return res.render("register", { error: "All fields are required" });
  }

  if (password !== confirm) {
    return res.render("register", { error: "Passwords do not match" });
  }

  if (password.length < 6) {
    return res.render("register", { error: "Password must be at least 6 characters" });
  }

  if (username.length < 3 || username.length > 20) {
    return res.render("register", { error: "Username must be 3-20 characters" });
  }

  try {
    createUser(username, password);
  } catch {
    return res.render("register", { error: "Username already taken" });
  }

  res.redirect("/login");
});

app.get("/logout", (req, res) => {
  req.session.destroy();
  res.redirect("/login");
});

app.get("/dashboard", requireLogin, (req, res) => {
  const user = findUserById(req.session.userId);
  if (!user) {
    req.session.destroy();
    return res.redirect("/login");
  }
  res.render("dashboard", { user, csrf: req.session.csrf });
});

app.all(
  "/account/change-password",
  requireLogin,
  csrfOnPostOnly,
  (req, res) => {
    if (!["GET", "POST"].includes(req.method)) {
      return res.sendStatus(405);
    }

    if (req.method === "GET" && !req.body?.password) {
      return res.render("change-password", { csrf: req.session.csrf });
    }

    const { password, confirm } = req.body ?? {};

    if (!password || password !== confirm || password.length < 8) {
      return res
        .status(400)
        .send("Password and confirmation must match (min 8 chars)");
    }

    changePassword(req.session.userId, password);
    res.send("Password changed successfully");
  }
);

app.get("/flag", requireLogin, (req, res) => {
  const user = findUserById(req.session.userId);
  if (!user || user.role !== "admin") {
    return res.status(403).render("flag", { flag: null });
  }
  res.render("flag", { flag: FLAG });
});

app.get("/report", requireLogin, (req, res) => {
  res.render("report", { result: null });
});

app.post("/report", requireLogin, async (req, res) => {
  const { url } = req.body;

  if (!url) {
    return res.render("report", { result: { success: false, error: "Page path is required" } });
  }

  if (!url.startsWith("/pages/") || url.includes("..")) {
    return res.render("report", {
      result: { success: false, error: "Path must start with /pages/" },
    });
  }

  const result = await visitPage(url);
  res.render("report", { result });
});

app.get("/pages/create", requireLogin, (req, res) => {
  res.render("create-page", { result: null });
});

app.post("/pages/upload", requireLogin, (req, res) => {
  const { html } = req.body;
  if (!html || html.length > 1024 * 50) {
    return res.status(400).json({ error: "HTML content required (max 50KB)" });
  }

  const id = uuidv4();
  const filename = `${id}.html`;
  fs.writeFileSync(path.join(PAGES_DIR, filename), html);

  const pageUrl = `/pages/${filename}`;
  if (req.headers.accept?.includes("application/json")) {
    return res.json({ url: pageUrl });
  }
  res.render("create-page", { result: { url: pageUrl } });
});

app.get("/pages/:file", (req, res) => {
  const file = path.basename(req.params.file);
  const filePath = path.join(PAGES_DIR, file);

  if (!fs.existsSync(filePath)) {
    return res.status(404).send("Page not found");
  }

  res.set(
    "Content-Security-Policy",
    "sandbox allow-scripts allow-forms allow-same-origin; connect-src 'none'; frame-src 'none'; object-src 'none'"
  );
  res.type("html").send(fs.readFileSync(filePath, "utf8"));
});

app.listen(3000);
