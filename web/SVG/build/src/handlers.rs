use crate::{
    state::{
        AppState, BrandForm, HomeQuery, LoginFormData, LoginQuery, PortalQuery, ReviewFormData,
        ReviewRun,
    },
    util::{
        authorized, default_svg_template, get_portal, not_found_page, push_review_run, redirect_to,
        render_review_runs, sanitize_svg, text_response, trimmed_output, update_review_run,
    },
    views::{render_login_page, site_shell},
};
use axum::{
    extract::{Form, Path, Query, State},
    http::{HeaderMap, HeaderValue, StatusCode, header::SET_COOKIE},
    response::{Html, IntoResponse, Response},
};
use html_escape::encode_text;
use std::process::Stdio;
use tokio::process::Command;
use uuid::Uuid;

pub async fn home(Query(query): Query<HomeQuery>) -> Html<String> {
    let notice = if query.created.as_deref() == Some("1") {
        "<div class=\"notice\">Portal created.</div>"
    } else {
        ""
    };

    Html(site_shell(
        "Northstar Workspace",
        "Hosted brand portals for partner sign-in",
        &format!(
            r#"{notice}
<section class="hero-grid">
  <div class="hero-copy">
    <p class="eyebrow">Hosted Authentication</p>
    <h1>Brand a login page without rebuilding your sign-in stack.</h1>
    <p class="lede">Northstar gives operations teams a managed sign-in surface for contractors, vendors, and temporary partner access. Upload a brand asset, confirm support details, and publish a login portal in minutes.</p>
    <div class="cta-row">
      <a class="button primary" href="/brand-kit">Create Portal</a>
    </div>
  </div>
  <div class="hero-card">
    <h3>Included</h3>
    <ul class="feature-list">
      <li>Branded sign-in page generation</li>
      <li>Managed logo and layout rendering</li>
      <li>Launch review workflow before rollout</li>
    </ul>
  </div>
</section>
<section class="info-grid">
  <article class="card">
    <p class="eyebrow">Partner Launch</p>
    <h2>Upload logos</h2>
    <p>Each partner gets a dedicated login portal with its own branding and support details.</p>
  </article>
  <article class="card">
    <p class="eyebrow">Internal Review</p>
    <h2>Security approval</h2>
    <p>New partner portals can be submitted for review before access is approved.</p>
  </article>
  <article class="card">
    <p class="eyebrow">Shared Auth</p>
    <h2>Single backend</h2>
    <p>Northstar keeps credential verification centralized while partners control their presentation layer.</p>
  </article>
</section>"#
        ),
    ))
}

pub async fn brand_kit_form() -> Html<String> {
    Html(site_shell(
        "Brand Kit",
        "Create a branded login portal",
        &format!(
            r#"<section class="card narrow">
<p class="eyebrow">Portal Builder</p>
<h1>Upload partner branding</h1>
<p>Provide a company name, support contact, and a logo asset. Northstar will generate a hosted sign-in page automatically.</p>
<form action="/brand-kit" method="post" class="stack">
  <label>Company name<input name="brand_name" value="Helio Freight" /></label>
  <label>Subtitle<input name="subtitle" value="Carrier access workspace" /></label>
  <label>Support email<input name="support_email" value="support@heliofreight.example" /></label>
  <label>Logo SVG<textarea name="logo_svg" spellcheck="false">{}</textarea></label>
  <button class="button primary" type="submit">Create Portal</button>
</form>
</section>
<section class="card subtle">
  <h2>Asset handling</h2>
  <p>Uploaded logo assets are normalized for display and embedded directly into the final login page.</p>
</section>"#,
            encode_text(&default_svg_template())
        ),
    ))
}

pub async fn create_portal(
    State(state): State<AppState>,
    Form(form): Form<BrandForm>,
) -> Result<Response, (StatusCode, Html<String>)> {
    let sanitized_svg = sanitize_svg(&form.logo_svg).map_err(|err| {
        (
            StatusCode::BAD_REQUEST,
            Html(site_shell(
                "Upload Failed",
                "SVG could not be processed",
                &format!(
                    r#"<section class="card narrow">
<p class="eyebrow">Upload Failed</p>
<h1>SVG rejected</h1>
<pre>{}</pre>
<a class="button ghost" href="/brand-kit">Back</a>
</section>"#,
                    encode_text(&err)
                ),
            )),
        )
    })?;

    let id = Uuid::new_v4();
    state
        .portals
        .write()
        .expect("portal write lock poisoned")
        .insert(
            id,
            crate::state::Portal {
                brand_name: form.brand_name,
                subtitle: form.subtitle,
                support_email: form.support_email,
                sanitized_svg,
            },
        );
    state
        .review_runs
        .write()
        .expect("review write lock poisoned")
        .entry(id)
        .or_default();

    Ok(redirect_to(&format!("/brand-kit/{id}?review=created")))
}

pub async fn portal_admin_page(
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
    Query(query): Query<PortalQuery>,
) -> Result<Html<String>, (StatusCode, Html<String>)> {
    let portal = get_portal(&state, id).ok_or_else(not_found_page)?;
    let notice = match query.review.as_deref() {
        Some("queued") => "<div class=\"notice\">Review requested. The access team will validate the sign-in flow shortly.</div>",
        Some("created") => "<div class=\"notice\">Portal created.</div>",
        _ => "",
    };

    Ok(Html(site_shell(
        &portal.brand_name,
        "Portal details",
        &format!(
            r#"{notice}
<section class="card">
  <p class="eyebrow">Portal</p>
  <h1>{brand}</h1>
  <p>{subtitle}</p>
  <div class="meta-grid">
    <div><span>Support</span><strong>{email}</strong></div>
    <div><span>Login URL</span><strong>{origin}/portal/{id}/login</strong></div>
  </div>
  <div class="cta-row">
    <a class="button primary" href="/portal/{id}/login">Open Login Page</a>
    <a class="button ghost" href="/assets/sanitized/{id}">Sanitized SVG</a>
  </div>
</section>
<section class="card">
  <p class="eyebrow">Launch Review</p>
  <h2>Request access-team validation</h2>
  <p>Use this before the portal is approved for production access.</p>
  <form action="/review" method="post">
    <input type="hidden" name="portal_id" value="{id}" />
    <button class="button primary" type="submit">Request Review</button>
  </form>
</section>
<section class="card">
  <p class="eyebrow">Recent activity</p>
  <h2>Activity</h2>
  {runs}
</section>"#,
            brand = encode_text(&portal.brand_name),
            subtitle = encode_text(&portal.subtitle),
            email = encode_text(&portal.support_email),
            origin = encode_text(&state.site_origin),
            runs = render_review_runs(&state, id),
        ),
    )))
}

pub async fn portal_login_page(
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
    Query(query): Query<LoginQuery>,
) -> Result<Html<String>, (StatusCode, Html<String>)> {
    let portal = get_portal(&state, id).ok_or_else(not_found_page)?;
    Ok(Html(render_login_page(
        &portal.brand_name,
        &portal.subtitle,
        &portal.support_email,
        &portal.sanitized_svg,
        id,
        query.error.is_some(),
    )))
}

pub async fn review_portal(
    State(state): State<AppState>,
    Form(form): Form<ReviewFormData>,
) -> Result<Response, (StatusCode, Html<String>)> {
    if get_portal(&state, form.portal_id).is_none() {
        return Err(not_found_page());
    }

    let run_id = Uuid::new_v4();
    push_review_run(
        &state,
        form.portal_id,
        ReviewRun {
            id: run_id,
            status: String::from("queued"),
            detail: String::from("waiting for bot"),
        },
    );

    let state_for_task = state.clone();
    tokio::spawn(async move {
        update_review_run(
            &state_for_task,
            form.portal_id,
            run_id,
            "running",
            "opening login page",
        );

        let target_url = format!("{}/portal/{}/login", state_for_task.site_origin, form.portal_id);
        let output = Command::new(&state_for_task.bot_command)
            .arg(&state_for_task.bot_script)
            .arg(&target_url)
            .env("BOT_USERNAME", &state_for_task.creds.username)
            .env("BOT_PASSWORD", &state_for_task.creds.password)
            .stdout(Stdio::piped())
            .stderr(Stdio::piped())
            .output()
            .await;

        match output {
            Ok(output) if output.status.success() => {
                update_review_run(
                    &state_for_task,
                    form.portal_id,
                    run_id,
                    "done",
                    &trimmed_output(&output.stdout, "review completed"),
                );
            }
            Ok(output) => {
                update_review_run(
                    &state_for_task,
                    form.portal_id,
                    run_id,
                    "failed",
                    &trimmed_output(&output.stderr, "bot failed"),
                );
            }
            Err(err) => {
                update_review_run(
                    &state_for_task,
                    form.portal_id,
                    run_id,
                    "failed",
                    &format!("failed to start bot: {err}"),
                );
            }
        }
    });

    Ok(redirect_to(&format!("/brand-kit/{}?review=queued", form.portal_id)))
}

pub async fn login(State(state): State<AppState>, Form(form): Form<LoginFormData>) -> Response {
    if form.uname == state.creds.username && form.passwd == state.creds.password {
        let session_id = Uuid::new_v4().to_string();
        state
            .sessions
            .write()
            .expect("session write lock poisoned")
            .insert(session_id.clone());

        let mut response = redirect_to("/workspace");
        let cookie = format!("session={session_id}; HttpOnly; Path=/; SameSite=Lax");
        response
            .headers_mut()
            .insert(SET_COOKIE, HeaderValue::from_str(&cookie).expect("valid cookie"));
        return response;
    }

    if let Some(portal_id) = form.portal_id {
        return redirect_to(&format!("/portal/{portal_id}/login?error=1"));
    }

    redirect_to("/")
}

pub async fn workspace_page(State(state): State<AppState>, headers: HeaderMap) -> Response {
    if !authorized(&state, &headers) {
        return redirect_to("/");
    }

    Html(site_shell(
        "Workspace",
        "Internal account dashboard",
        &format!(
            r#"<section class="card narrow">
<p class="eyebrow">Authenticated</p>
<h1>Operations workspace</h1>
<p>You are signed into the internal account workspace.</p>
<div class="vault-flag">{}</div>
</section>"#,
            encode_text(&state.flag)
        ),
    ))
    .into_response()
}

pub async fn sanitized_svg(
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
) -> Result<Response, (StatusCode, Html<String>)> {
    let portal = get_portal(&state, id).ok_or_else(not_found_page)?;
    Ok(text_response("image/svg+xml; charset=utf-8", portal.sanitized_svg))
}
