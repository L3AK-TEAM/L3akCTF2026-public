mod handlers;
mod state;
mod util;
mod views;

use axum::{Router, routing::{get, post}};
use state::{AppState, Credentials};
use std::{collections::{HashMap, HashSet}, net::SocketAddr, sync::{Arc, RwLock}};
use tokio::task::JoinHandle;
use util::env_var_or;

#[tokio::main]
async fn main() {
    let state = AppState {
        site_origin: String::from("http://127.0.0.1:3000"),
        bot_command: String::from("node"),
        bot_script: String::from("/app/bot/bot.js"),
        creds: Credentials {
            username: String::from("23a9d8d2de1df569"),
            password: String::from("9f4df8f4849e26e7"),
        },
        flag: env_var_or("FLAG", "L3AK{1bff9bfa2ff0f26803498c4868804a5a}"),
        portals: Arc::new(RwLock::new(HashMap::new())),
        review_runs: Arc::new(RwLock::new(HashMap::new())),
        sessions: Arc::new(RwLock::new(HashSet::new())),
    };

    let app = Router::new()
        .route("/", get(handlers::home))
        .route("/brand-kit", get(handlers::brand_kit_form).post(handlers::create_portal))
        .route("/brand-kit/{id}", get(handlers::portal_admin_page))
        .route("/portal/{id}/login", get(handlers::portal_login_page))
        .route("/review", post(handlers::review_portal))
        .route("/login", post(handlers::login))
        .route("/workspace", get(handlers::workspace_page))
        .route("/assets/sanitized/{id}", get(handlers::sanitized_svg))
        .with_state(state.clone());

    println!("site origin: {}", state.site_origin);
    println!("bot command: {} {}", state.bot_command, state.bot_script);

    let addr: SocketAddr = "0.0.0.0:3000".parse().expect("valid bind");
    let listener = tokio::net::TcpListener::bind(addr)
        .await
        .expect("failed to bind listener");

    let task = spawn_server(async move {
        axum::serve(listener, app)
            .await
            .map_err(std::io::Error::other)
    });

    tokio::signal::ctrl_c()
        .await
        .expect("failed waiting for shutdown signal");
    task.abort();
}

fn spawn_server<S>(server: S) -> JoinHandle<()>
where
    S: std::future::Future<Output = Result<(), std::io::Error>> + Send + 'static,
{
    tokio::spawn(async move {
        if let Err(err) = server.await {
            eprintln!("server error: {err}");
        }
    })
}
