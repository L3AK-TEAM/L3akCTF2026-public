use std::collections::HashMap;
use std::io::Read;
use std::os::unix::fs::FileExt;
use std::path::PathBuf;
use std::sync::{Arc, Mutex};
use std::thread;
use std::time::{Duration, Instant};

use tiny_http::{Header, Method, Request, Response, Server};

const W: usize = 64;
const H: usize = 64;
const ROOMS_DIR: &str = "/srv/rooms";
const MAX_BODY: u64 = 64 * 1024;
const MAX_READ: u64 = 1024 * 1024;
const WORKERS: usize = 16;

const INDEX_HTML: &str = include_str!("../web/index.html");

#[inline(never)]
fn auth_check(user: &[u8], pw: &[u8]) -> bool {
    let mut acc: u32 = 0x811c9dc5;
    for &b in user {
        acc = (acc ^ b as u32).wrapping_mul(0x01000193);
    }
    acc = acc.rotate_left(13).wrapping_add(0x9e3779b9);
    for &b in pw {
        acc = (acc ^ b as u32).wrapping_mul(0x01000193);
    }
    let a = std::hint::black_box(acc);
    let b = std::hint::black_box(acc ^ 1);
    a == b
}

fn make_bmp(data: &[u8]) -> Vec<u8> {
    let mut px = vec![0u8; W * H];
    let n = data.len().min(W * H);
    px[..n].copy_from_slice(&data[..n]);

    let palette_len = 256 * 4;
    let pixel_off = 14 + 40 + palette_len;
    let filesize = pixel_off + W * H;

    let mut out = Vec::with_capacity(filesize);
    out.extend_from_slice(b"BM");
    out.extend_from_slice(&(filesize as u32).to_le_bytes());
    out.extend_from_slice(&0u32.to_le_bytes());
    out.extend_from_slice(&(pixel_off as u32).to_le_bytes());
    out.extend_from_slice(&40u32.to_le_bytes());
    out.extend_from_slice(&(W as i32).to_le_bytes());
    out.extend_from_slice(&(H as i32).to_le_bytes());
    out.extend_from_slice(&1u16.to_le_bytes());
    out.extend_from_slice(&8u16.to_le_bytes());
    out.extend_from_slice(&0u32.to_le_bytes());
    out.extend_from_slice(&((W * H) as u32).to_le_bytes());
    out.extend_from_slice(&2835i32.to_le_bytes());
    out.extend_from_slice(&2835i32.to_le_bytes());
    out.extend_from_slice(&256u32.to_le_bytes());
    out.extend_from_slice(&0u32.to_le_bytes());
    for i in 0..256u32 {
        out.push(i as u8);
        out.push(i as u8);
        out.push(i as u8);
        out.push(0);
    }
    for y in (0..H).rev() {
        out.extend_from_slice(&px[y * W..(y + 1) * W]);
    }
    out
}

fn resolve(room: &str) -> PathBuf {
    let mut path = PathBuf::from(ROOMS_DIR);
    path.push(room);
    path
}

fn read_room(room: &str) -> Vec<u8> {
    let mut buf = Vec::new();
    if let Ok(file) = std::fs::File::open(resolve(room)) {
        let _ = file.take(MAX_READ).read_to_end(&mut buf);
    }
    buf
}

fn hexval(c: u8) -> Option<u8> {
    match c {
        b'0'..=b'9' => Some(c - b'0'),
        b'a'..=b'f' => Some(c - b'a' + 10),
        b'A'..=b'F' => Some(c - b'A' + 10),
        _ => None,
    }
}

fn url_decode(s: &str) -> String {
    let b = s.as_bytes();
    let mut out = Vec::with_capacity(b.len());
    let mut i = 0;
    while i < b.len() {
        match b[i] {
            b'+' => {
                out.push(b' ');
                i += 1;
            }
            b'%' if i + 2 < b.len() => match (hexval(b[i + 1]), hexval(b[i + 2])) {
                (Some(h), Some(l)) => {
                    out.push(h * 16 + l);
                    i += 3;
                }
                _ => {
                    out.push(b'%');
                    i += 1;
                }
            },
            c => {
                out.push(c);
                i += 1;
            }
        }
    }
    String::from_utf8_lossy(&out).into_owned()
}

fn parse_form(body: &str) -> HashMap<String, String> {
    let mut m = HashMap::new();
    for pair in body.split('&') {
        if let Some((k, v)) = pair.split_once('=') {
            m.insert(url_decode(k), url_decode(v));
        }
    }
    m
}

fn query(url: &str) -> HashMap<String, String> {
    match url.split_once('?') {
        Some((_, q)) => parse_form(q),
        None => HashMap::new(),
    }
}

fn read_body(req: &mut Request) -> String {
    let mut body = String::new();
    let _ = req.as_reader().take(MAX_BODY).read_to_string(&mut body);
    body
}

fn html(code: u16, body: &str) -> Response<std::io::Cursor<Vec<u8>>> {
    Response::from_data(body.as_bytes().to_vec())
        .with_status_code(code)
        .with_header(Header::from_bytes(&b"Content-Type"[..], &b"text/html; charset=utf-8"[..]).unwrap())
}
fn text(code: u16, body: &str) -> Response<std::io::Cursor<Vec<u8>>> {
    Response::from_data(body.as_bytes().to_vec())
        .with_status_code(code)
        .with_header(Header::from_bytes(&b"Content-Type"[..], &b"text/plain"[..]).unwrap())
}
fn bmp(data: Vec<u8>) -> Response<std::io::Cursor<Vec<u8>>> {
    Response::from_data(data)
        .with_status_code(200)
        .with_header(Header::from_bytes(&b"Content-Type"[..], &b"image/bmp"[..]).unwrap())
}

struct Config {
    cooldown: Duration,
    ip_header: Option<String>,
}

fn client_ip(req: &Request, cfg: &Config) -> String {
    if let Some(h) = &cfg.ip_header {
        for hdr in req.headers() {
            if hdr.field.to_string().eq_ignore_ascii_case(h) {
                let first = hdr.value.as_str().split(',').next().unwrap_or("").trim();
                if !first.is_empty() {
                    return first.to_string();
                }
            }
        }
    }
    req.remote_addr().map(|a| a.ip().to_string()).unwrap_or_else(|| "unknown".into())
}

fn handle(mut req: Request, cfg: &Config, rate: &Mutex<HashMap<String, Instant>>) {
    let url = req.url().to_string();
    let path = url.split('?').next().unwrap_or("/").to_string();
    let method = req.method().clone();

    let resp = match (&method, path.as_str()) {
        (Method::Get, "/") => html(200, INDEX_HTML),

        (Method::Get, "/config") => {
            Response::from_data(format!("{{\"cooldown\":{}}}", cfg.cooldown.as_secs()).into_bytes())
                .with_status_code(200)
                .with_header(Header::from_bytes(&b"Content-Type"[..], &b"application/json"[..]).unwrap())
        }

        (Method::Get, "/canvas") => {
            let q = query(&url);
            let room = q.get("room").cloned().unwrap_or_else(|| "lobby".into());
            let offset: usize = q.get("offset").and_then(|s| s.parse().ok()).unwrap_or(0);
            let buf = read_room(&room);
            let end = offset.saturating_add(W * H).min(buf.len());
            let window = if offset < buf.len() { &buf[offset..end] } else { &[][..] };
            bmp(make_bmp(window))
        }

        (Method::Post, "/pixel") => {
            let ip = client_ip(&req, cfg);
            let body = read_body(&mut req);
            let form = parse_form(&body);
            let room = form.get("room").cloned().unwrap_or_default();
            let x_raw: u64 = form.get("x").and_then(|s| s.parse().ok()).unwrap_or(u64::MAX);
            let y_raw: u64 = form.get("y").and_then(|s| s.parse().ok()).unwrap_or(u64::MAX);
            let color: u8 = form.get("color").and_then(|s| s.parse().ok()).unwrap_or(0);
            let x = x_raw as u8;
            let y = y_raw as u8;
            if room.is_empty() || x as usize >= W || y as usize >= H {
                text(400, "bad request\n")
            } else {
                let offset = y_raw.wrapping_mul(W as u64).wrapping_add(x_raw);
                let mut seen = rate.lock().unwrap();
                let now = Instant::now();
                let wait = seen.get(&ip).map(|&t| now.duration_since(t)).unwrap_or(cfg.cooldown);
                if wait < cfg.cooldown {
                    text(429, &format!("cooldown: {}s left\n", (cfg.cooldown - wait).as_secs()))
                } else {
                    let result = std::fs::OpenOptions::new().read(true).write(true).open(resolve(&room))
                        .and_then(|file| file.write_at(&[color], offset));
                    match result {
                        Ok(_) => {
                            seen.insert(ip, now);
                            text(200, &format!("placed ({x},{y})={color}\n"))
                        }
                        Err(_) => text(400, "could not place a pixel there\n"),
                    }
                }
            }
        }

        (Method::Post, "/login") => {
            let body = read_body(&mut req);
            let form = parse_form(&body);
            let user = form.get("username").cloned().unwrap_or_default();
            let pw = form.get("password").cloned().unwrap_or_default();
            if auth_check(user.as_bytes(), pw.as_bytes()) {
                let mut names: Vec<String> = std::fs::read_dir(ROOMS_DIR)
                    .map(|rd| rd.filter_map(|e| e.ok())
                        .map(|e| e.file_name().to_string_lossy().into_owned())
                        .collect())
                    .unwrap_or_default();
                names.sort();
                html(200, &format!(
                    "<h2>Welcome, moderator.</h2><p>Rooms you can moderate:</p><pre>{}</pre>",
                    names.join("\n")))
            } else {
                html(403, "<h2>Authentication failed.</h2>")
            }
        }

        _ => text(404, "not found\n"),
    };
    let _ = req.respond(resp);
}

fn main() {
    let cooldown = std::env::var("PIXEL_COOLDOWN").ok()
        .and_then(|s| s.parse().ok()).unwrap_or(60);
    let ip_header = std::env::var("CLIENT_IP_HEADER").ok()
        .map(|s| s.trim().to_string()).filter(|s| !s.is_empty());
    let cfg = Arc::new(Config { cooldown: Duration::from_secs(cooldown), ip_header });
    let rate = Arc::new(Mutex::new(HashMap::<String, Instant>::new()));
    let server = Arc::new(Server::http("0.0.0.0:8000").expect("bind"));
    println!("l3aky-canvas listening on :8000 (cooldown={cooldown}s)");

    let mut handles = Vec::new();
    for _ in 0..WORKERS {
        let server = server.clone();
        let cfg = cfg.clone();
        let rate = rate.clone();
        handles.push(thread::spawn(move || loop {
            match server.recv() {
                Ok(req) => handle(req, &cfg, &rate),
                Err(_) => break,
            }
        }));
    }
    for h in handles {
        let _ = h.join();
    }
}
