use serde::Deserialize;
use std::{
    collections::{HashMap, HashSet},
    sync::{Arc, RwLock},
};
use uuid::Uuid;

#[derive(Clone)]
pub struct AppState {
    pub site_origin: String,
    pub bot_command: String,
    pub bot_script: String,
    pub creds: Credentials,
    pub flag: String,
    pub portals: Arc<RwLock<HashMap<Uuid, Portal>>>,
    pub review_runs: Arc<RwLock<HashMap<Uuid, Vec<ReviewRun>>>>,
    pub sessions: Arc<RwLock<HashSet<String>>>,
}

#[derive(Clone)]
pub struct Credentials {
    pub username: String,
    pub password: String,
}

#[derive(Clone)]
pub struct Portal {
    pub brand_name: String,
    pub subtitle: String,
    pub support_email: String,
    pub sanitized_svg: String,
}

#[derive(Clone)]
pub struct ReviewRun {
    pub id: Uuid,
    pub status: String,
    pub detail: String,
}

#[derive(Deserialize)]
pub struct BrandForm {
    pub brand_name: String,
    pub subtitle: String,
    pub support_email: String,
    pub logo_svg: String,
}

#[derive(Deserialize)]
pub struct LoginFormData {
    pub uname: String,
    pub passwd: String,
    pub portal_id: Option<Uuid>,
}

#[derive(Deserialize)]
pub struct ReviewFormData {
    pub portal_id: Uuid,
}

#[derive(Deserialize)]
pub struct HomeQuery {
    pub created: Option<String>,
}

#[derive(Deserialize)]
pub struct PortalQuery {
    pub review: Option<String>,
}

#[derive(Deserialize)]
pub struct LoginQuery {
    pub error: Option<String>,
}
