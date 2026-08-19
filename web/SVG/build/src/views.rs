use html_escape::encode_text;
use uuid::Uuid;

pub fn render_login_page(
    brand_name: &str,
    subtitle: &str,
    support_email: &str,
    sanitized_svg: &str,
    portal_id: Uuid,
    show_error: bool,
) -> String {
    let error_block = if show_error {
        "<div class=\"error-box\">The username or password was rejected.</div>"
    } else {
        ""
    };

    format!(
        r#"<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>{brand_name} Sign In</title>
<style>
:root {{
  --page: #f3efe8;
  --text: #16181b;
  --muted: #66727d;
  --panel: rgba(255,255,255,0.92);
  --stroke: rgba(22,24,27,0.1);
  --accent: #0d4d6e;
  --accent-2: #bc5b2c;
}}
* {{ box-sizing: border-box; }}
body {{
  margin: 0;
  min-height: 100vh;
  font-family: "IBM Plex Sans", "Segoe UI", sans-serif;
  color: var(--text);
  background:
    radial-gradient(circle at top left, rgba(13,77,110,0.22), transparent 28%),
    radial-gradient(circle at bottom right, rgba(188,91,44,0.18), transparent 32%),
    linear-gradient(180deg, #f9f7f3, var(--page));
}}
.layout {{
  width: min(1080px, calc(100% - 32px));
  margin: 36px auto;
  display: grid;
  grid-template-columns: 1.2fr 0.95fr;
  gap: 24px;
  align-items: stretch;
}}
.brand-panel, .form-panel {{
  border: 1px solid var(--stroke);
  background: var(--panel);
  border-radius: 28px;
  box-shadow: 0 24px 80px rgba(27, 38, 49, 0.08);
}}
.brand-panel {{
  padding: 34px;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
}}
.brand-mark {{
  padding: 18px;
  min-height: 140px;
  border-radius: 22px;
  background: linear-gradient(135deg, rgba(13,77,110,0.06), rgba(188,91,44,0.05));
  border: 1px solid rgba(13,77,110,0.12);
}}
.brand-panel h1 {{
  margin: 22px 0 8px;
  font-size: clamp(2.3rem, 4vw, 4rem);
  line-height: 0.95;
}}
.brand-panel p {{
  margin: 0;
  color: var(--muted);
  max-width: 36rem;
  font-size: 1.05rem;
}}
.support-row {{
  margin-top: 18px;
  padding-top: 18px;
  border-top: 1px solid rgba(22,24,27,0.08);
  display: flex;
  justify-content: space-between;
  gap: 12px;
  color: var(--muted);
}}
.support-row strong {{ color: var(--text); }}
.form-panel {{ padding: 34px; }}
.eyebrow {{
  text-transform: uppercase;
  letter-spacing: 0.12em;
  font-size: 0.78rem;
  color: var(--accent);
  font-weight: 700;
}}
.form-panel h2 {{
  margin: 10px 0 8px;
  font-size: 2rem;
}}
.form-panel p {{
  color: var(--muted);
  margin: 0 0 22px;
}}
label {{
  display: block;
  margin: 0 0 14px;
  font-size: 0.95rem;
  color: #2c333a;
}}
input {{
  width: 100%;
  margin-top: 8px;
  padding: 14px 16px;
  border-radius: 14px;
  border: 1px solid rgba(22,24,27,0.12);
  font: inherit;
  background: white;
}}
button {{
  width: 100%;
  margin-top: 8px;
  border: 0;
  border-radius: 14px;
  padding: 15px 18px;
  background: linear-gradient(135deg, var(--accent), #0f6e87);
  color: white;
  font: inherit;
  font-weight: 700;
  cursor: pointer;
}}
.error-box {{
  margin-bottom: 16px;
  padding: 12px 14px;
  border-radius: 12px;
  background: rgba(188,91,44,0.12);
  color: #8f3a11;
}}
.footnote {{
  margin-top: 18px;
  color: var(--muted);
  font-size: 0.92rem;
}}
@media (max-width: 900px) {{
  .layout {{ grid-template-columns: 1fr; }}
}}
</style>
</head>
<body>
<main class="layout">
  <aside class="brand-panel">
    <div>
      <div class="brand-mark">{sanitized_svg}</div>
      <h1>{brand_name}</h1>
      <p>{subtitle}</p>
    </div>
    <div>
      <div class="support-row"><span>Support</span><strong>{support_email}</strong></div>
      <p class="footnote">Northstar Workspace provides the shared authentication layer for approved partner access pages.</p>
    </div>
  </aside>
  <section class="form-panel">
    <p class="eyebrow">Workspace Access</p>
    <h2>Sign in</h2>
    <p>Use your issued username and password to continue.</p>
    {error_block}
    <form action="/login" method="post" autocomplete="off">
      <input type="hidden" name="portal_id" value="{portal_id}" />
      <label for="uname">Username<input id="uname" name="uname" type="text" /></label>
      <label for="passwd">Password<input id="passwd" name="passwd" type="text" /></label>
      <button type="submit">Continue</button>
    </form>
    <p class="footnote">Need access? Contact your organization administrator.</p>
  </section>
</main>
<script>
for (const id of ["uname", "passwd"]) {{
  const el = document.getElementById(id);
  if (!el) continue;
  const sync = () => el.setAttribute("value", el.value);
  sync();
  el.addEventListener("input", sync);
  el.addEventListener("change", sync);
}}
</script>
</body>
</html>"#,
        brand_name = encode_text(brand_name),
        subtitle = encode_text(subtitle),
        support_email = encode_text(support_email),
        sanitized_svg = sanitized_svg,
        error_block = error_block,
        portal_id = portal_id,
    )
}

pub fn site_shell(title: &str, subtitle: &str, body: &str) -> String {
    format!(
        r#"<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>{title}</title>
<style>
:root {{
  --bg: #f6f0e7;
  --ink: #18202a;
  --card: rgba(255,255,255,0.9);
  --line: rgba(24,32,42,0.1);
  --accent: #0d4d6e;
  --accent-2: #bc5b2c;
}}
* {{ box-sizing: border-box; }}
body {{
  margin: 0;
  font-family: "IBM Plex Sans", "Segoe UI", sans-serif;
  color: var(--ink);
  background:
    radial-gradient(circle at top left, rgba(13,77,110,0.18), transparent 30%),
    radial-gradient(circle at bottom right, rgba(188,91,44,0.16), transparent 34%),
    linear-gradient(180deg, #fbf8f3, var(--bg));
}}
.site {{
  width: min(1120px, calc(100% - 32px));
  margin: 24px auto 48px;
}}
.topbar {{
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 16px;
  padding: 14px 0 18px;
}}
.brand strong {{
  font-size: 1.05rem;
}}
.brand span {{
  display: block;
  color: #56606b;
  font-size: 0.9rem;
  margin-top: 2px;
}}
nav {{ display: flex; gap: 16px; flex-wrap: wrap; }}
nav a {{
  color: inherit;
  text-decoration: none;
  opacity: 0.82;
}}
.hero {{
  border: 1px solid var(--line);
  background: var(--card);
  border-radius: 28px;
  padding: 28px;
  box-shadow: 0 18px 64px rgba(20, 28, 36, 0.08);
  margin-bottom: 20px;
}}
.hero h1 {{
  margin: 12px 0 10px;
  font-size: clamp(2.2rem, 5vw, 4.4rem);
  line-height: 0.95;
}}
.hero p {{
  margin: 0;
  color: #5d6771;
  max-width: 42rem;
}}
.eyebrow {{
  text-transform: uppercase;
  letter-spacing: 0.12em;
  font-size: 0.78rem;
  color: var(--accent);
  font-weight: 700;
}}
.hero-grid, .info-grid {{
  display: grid;
  gap: 20px;
}}
.hero-grid {{
  grid-template-columns: 1.25fr 0.8fr;
  align-items: stretch;
}}
.info-grid {{
  grid-template-columns: repeat(3, minmax(0, 1fr));
}}
.hero-card, .card {{
  border: 1px solid var(--line);
  background: var(--card);
  border-radius: 24px;
  padding: 24px;
  box-shadow: 0 18px 64px rgba(20, 28, 36, 0.06);
  margin-bottom: 20px;
}}
.card.narrow {{ max-width: 760px; }}
.card.subtle {{
  background: linear-gradient(135deg, rgba(255,255,255,0.88), rgba(255,255,255,0.72));
}}
.feature-list {{
  margin: 14px 0 0;
  padding-left: 20px;
  color: #4f5964;
}}
.feature-list li {{ margin-bottom: 10px; }}
.stack label {{
  display: block;
  margin-bottom: 14px;
}}
input, textarea {{
  width: 100%;
  margin-top: 8px;
  border: 1px solid rgba(24,32,42,0.12);
  background: white;
  border-radius: 16px;
  padding: 14px 16px;
  font: inherit;
}}
textarea {{
  min-height: 240px;
  resize: vertical;
}}
.button {{
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 13px 18px;
  border-radius: 14px;
  text-decoration: none;
  border: 0;
  font: inherit;
  cursor: pointer;
}}
.button.primary {{
  background: linear-gradient(135deg, var(--accent), #0f6e87);
  color: white;
}}
.button.ghost {{
  background: rgba(255,255,255,0.72);
  color: var(--ink);
  border: 1px solid rgba(24,32,42,0.1);
}}
.cta-row {{
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
  margin-top: 22px;
}}
.notice {{
  margin-bottom: 18px;
  padding: 14px 16px;
  border-radius: 16px;
  background: rgba(13,77,110,0.12);
  color: #0f4b68;
}}
.meta-grid {{
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14px;
  margin: 18px 0 6px;
}}
.meta-grid span {{
  display: block;
  color: #66717d;
  font-size: 0.85rem;
}}
.meta-grid strong {{
  display: block;
  margin-top: 6px;
  overflow-wrap: anywhere;
}}
pre, code {{
  font-family: "IBM Plex Mono", "Iosevka Web", monospace;
}}
pre {{
  white-space: pre-wrap;
  overflow-wrap: anywhere;
  padding: 14px 16px;
  border-radius: 18px;
  border: 1px solid rgba(24,32,42,0.09);
  background: rgba(255,255,255,0.84);
}}
table {{
  width: 100%;
  border-collapse: collapse;
}}
th, td {{
  text-align: left;
  padding: 12px 10px;
  border-bottom: 1px solid rgba(24,32,42,0.08);
  vertical-align: top;
}}
.vault-flag {{
  margin-top: 18px;
  padding: 18px;
  border-radius: 18px;
  background: linear-gradient(135deg, rgba(13,77,110,0.1), rgba(188,91,44,0.08));
  border: 1px solid rgba(13,77,110,0.16);
  font-family: "IBM Plex Mono", monospace;
}}
.status {{
  display: inline-block;
  padding: 6px 10px;
  border-radius: 999px;
  font-size: 0.85rem;
  font-weight: 700;
  text-transform: lowercase;
}}
.status-queued {{ background: rgba(113,162,255,0.16); color: #2d5dcc; }}
.status-running {{ background: rgba(126,240,207,0.18); color: #166c57; }}
.status-done {{ background: rgba(60,179,113,0.16); color: #1f7a46; }}
.status-failed {{ background: rgba(188,91,44,0.16); color: #8f3f15; }}
@media (max-width: 920px) {{
  .hero-grid, .info-grid, .meta-grid {{ grid-template-columns: 1fr; }}
  .topbar {{ flex-direction: column; align-items: flex-start; }}
}}
</style>
</head>
<body>
<main class="site">
  <header class="topbar">
    <div class="brand">
      <strong>Northstar Workspace</strong>
      <span>{subtitle}</span>
    </div>
    <nav>
      <a href="/">Home</a>
      <a href="/brand-kit">Brand Kit</a>
    </nav>
  </header>
  <section class="hero">
    <p class="eyebrow">Hosted Authentication</p>
    <h1>{title}</h1>
    <p>{subtitle}</p>
  </section>
  {body}
</main>
</body>
</html>"#,
        title = encode_text(title),
        subtitle = encode_text(subtitle),
        body = body,
    )
}
