use crate::state::{AppState, Portal, ReviewRun};
use axum::{
    http::{
        HeaderMap, HeaderValue, StatusCode,
        header::{CACHE_CONTROL, CONTENT_TYPE, LOCATION},
    },
    response::{Html, IntoResponse, Response},
};
use html_escape::encode_text;
use std::env;
use svg_hush::{Filter, data_url_filter};
use uuid::Uuid;

pub fn sanitize_svg(input: &str) -> Result<String, String> {
    let mut filter = Filter::new();
    filter.set_data_url_filter(data_url_filter::allow_standard_images);
    let mut output = Vec::new();
    filter
        .filter(input.as_bytes(), &mut output)
        .map_err(|err| err.to_string())?;
    String::from_utf8(output).map_err(|err| err.to_string())
}

pub fn get_portal(state: &AppState, id: Uuid) -> Option<Portal> {
    state
        .portals
        .read()
        .expect("portal read lock poisoned")
        .get(&id)
        .cloned()
}

pub fn push_review_run(state: &AppState, portal_id: Uuid, run: ReviewRun) {
    state
        .review_runs
        .write()
        .expect("review write lock poisoned")
        .entry(portal_id)
        .or_default()
        .insert(0, run);
}

pub fn update_review_run(state: &AppState, portal_id: Uuid, run_id: Uuid, status: &str, detail: &str) {
    if let Some(runs) = state
        .review_runs
        .write()
        .expect("review write lock poisoned")
        .get_mut(&portal_id)
    {
        if let Some(run) = runs.iter_mut().find(|run| run.id == run_id) {
            run.status = status.to_string();
            run.detail = detail.to_string();
        }
    }
}

pub fn authorized(state: &AppState, headers: &HeaderMap) -> bool {
    read_cookie(headers, "session")
        .as_deref()
        .map(|session_id| {
            state
                .sessions
                .read()
                .expect("session read lock poisoned")
                .contains(session_id)
        })
        .unwrap_or(false)
}

pub fn trimmed_output(bytes: &[u8], fallback: &str) -> String {
    let text = String::from_utf8_lossy(bytes).trim().to_string();
    if text.is_empty() {
        fallback.to_string()
    } else {
        text.lines().next().unwrap_or(fallback).to_string()
    }
}

pub fn text_response(content_type: &'static str, body: String) -> Response {
    (
        [
            (CONTENT_TYPE, content_type),
            (CACHE_CONTROL, "no-store, max-age=0"),
        ],
        body,
    )
        .into_response()
}

pub fn redirect_to(target: &str) -> Response {
    let mut response = Response::new(axum::body::Body::empty());
    *response.status_mut() = StatusCode::SEE_OTHER;
    response
        .headers_mut()
        .insert(LOCATION, HeaderValue::from_str(target).expect("valid redirect"));
    response
}

pub fn not_found_page() -> (StatusCode, Html<String>) {
    (
        StatusCode::NOT_FOUND,
        Html(crate::views::site_shell(
            "Not Found",
            "The requested resource does not exist",
            r#"<section class="card narrow"><p class="eyebrow">Missing</p><h1>Not found</h1><p>The requested page or asset could not be found.</p></section>"#,
        )),
    )
}

pub fn read_cookie(headers: &HeaderMap, name: &str) -> Option<String> {
    let raw = headers.get("cookie")?.to_str().ok()?;
    for cookie in raw.split(';') {
        let trimmed = cookie.trim();
        let (key, value) = trimmed.split_once('=')?;
        if key == name {
            return Some(value.to_string());
        }
    }
    None
}

pub fn env_var_or(name: &str, fallback: &str) -> String {
    env::var(name).unwrap_or_else(|_| fallback.to_string())
}

pub fn default_svg_template() -> String {
    String::from(
        r##"<svg xmlns="http://www.w3.org/2000/svg">
  <rect x="4" y="4" width="172" height="36" rx="10" fill="#0d4d6e"/>
  <circle cx="24" cy="22" r="8" fill="#bc5b2c"/>
  <text x="42" y="28" font-size="20" font-family="Verdana, sans-serif" fill="#ffffff">Helio Freight</text>
</svg>"##,
    )
}

pub fn render_review_runs(state: &AppState, portal_id: Uuid) -> String {
    let runs = state
        .review_runs
        .read()
        .expect("review read lock poisoned")
        .get(&portal_id)
        .cloned()
        .unwrap_or_default();

    if runs.is_empty() {
        return String::from("<p>No review activity yet.</p>");
    }

    let mut out = String::from(
        "<table><thead><tr><th>Run</th><th>Status</th><th>Detail</th></tr></thead><tbody>",
    );
    for run in runs {
        out.push_str(&format!(
            "<tr><td><code>{}</code></td><td><span class=\"status status-{}\">{}</span></td><td>{}</td></tr>",
            run.id,
            encode_text(&run.status),
            encode_text(&run.status),
            encode_text(&run.detail),
        ));
    }
    out.push_str("</tbody></table>");
    out
}
