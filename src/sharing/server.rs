// TimeSensei Mobile Sharing Web Server
// Matches sharing/server.py exactly using Axum and Tokio.

use std::net::SocketAddr;
use std::path::{Path, PathBuf};
use std::sync::Arc;
use std::time::{Duration, SystemTime};
use axum::{
    extract::{Path as AxPath, State},
    http::{header, StatusCode},
    response::{Html, IntoResponse, Redirect, Response},
    routing::get,
    Router,
};
use tower_http::services::ServeDir;
use crate::config;

#[derive(Clone)]
pub struct ServerState {
    pub captures_dir: PathBuf,
    pub template_path: PathBuf,
}

pub fn get_latest_capture_id(captures_dir: &Path) -> Option<String> {
    if let Ok(entries) = std::fs::read_dir(captures_dir) {
        let mut jpgs: Vec<(SystemTime, String)> = entries
            .filter_map(|e| e.ok())
            .filter_map(|e| {
                let path = e.path();
                if path.extension().and_then(|s| s.to_str()) == Some("jpg") {
                    let meta = e.metadata().ok()?;
                    let mtime = meta.modified().unwrap_or(SystemTime::UNIX_EPOCH);
                    let stem = path.file_stem()?.to_str()?.to_string();
                    Some((mtime, stem))
                } else {
                    None
                }
            })
            .collect();
        jpgs.sort_by(|a, b| b.0.cmp(&a.0));
        return jpgs.first().map(|(_, stem)| stem.clone());
    }
    None
}

async fn handle_root_or_latest(State(state): State<Arc<ServerState>>) -> Response {
    if let Some(latest) = get_latest_capture_id(&state.captures_dir) {
        Redirect::temporary(&format!("/photo/{}", latest)).into_response()
    } else {
        render_photo_html(&state.template_path, "waiting_for_first_capture").into_response()
    }
}

async fn handle_health() -> impl IntoResponse {
    axum::Json(serde_json::json!({
        "status": "ok",
        "app": config::APP_NAME
    }))
}

fn is_valid_photo_id(photo_id: &str) -> bool {
    !photo_id.is_empty()
        && photo_id.len() <= 64
        && photo_id.chars().all(|c| c.is_ascii_alphanumeric() || c == '_' || c == '-')
}

fn render_photo_html(template_path: &Path, photo_id: &str) -> Html<String> {
    let raw = std::fs::read_to_string(template_path).unwrap_or_else(|_| {
        format!(
            "<!DOCTYPE html><html><head><title>TimeSensei</title></head><body><h1>Photo ID: {}</h1><img src=\"/image/{}\" style=\"max-width:100%\"></body></html>",
            photo_id, photo_id
        )
    });
    // Replace template variables
    let rendered = raw
        .replace("{{ photo_id }}", photo_id)
        .replace("{{photo_id}}", photo_id);
    Html(rendered)
}

async fn handle_view_photo(
    AxPath(photo_id): AxPath<String>,
    State(state): State<Arc<ServerState>>,
) -> Response {
    if !is_valid_photo_id(&photo_id) {
        return (StatusCode::BAD_REQUEST, "Invalid photo ID").into_response();
    }
    let file_path = state.captures_dir.join(format!("{}.jpg", photo_id));
    if !file_path.exists() && photo_id != "waiting_for_first_capture" {
        return (StatusCode::NOT_FOUND, "Photo not found").into_response();
    }
    render_photo_html(&state.template_path, &photo_id).into_response()
}

async fn handle_get_image(
    AxPath(photo_id): AxPath<String>,
    State(state): State<Arc<ServerState>>,
) -> Response {
    if !is_valid_photo_id(&photo_id) {
        return (StatusCode::BAD_REQUEST, "Invalid photo ID").into_response();
    }
    let file_path = state.captures_dir.join(format!("{}.jpg", photo_id));
    if let Ok(bytes) = tokio::fs::read(&file_path).await {
        (
            [
                (header::CONTENT_TYPE, "image/jpeg"),
                (header::CACHE_CONTROL, "public, max-age=3600"),
            ],
            bytes,
        )
            .into_response()
    } else {
        (StatusCode::NOT_FOUND, "Image not found").into_response()
    }
}

async fn handle_download_image(
    AxPath(photo_id): AxPath<String>,
    State(state): State<Arc<ServerState>>,
) -> Response {
    if !is_valid_photo_id(&photo_id) {
        return (StatusCode::BAD_REQUEST, "Invalid photo ID").into_response();
    }
    let file_path = state.captures_dir.join(format!("{}.jpg", photo_id));
    if let Ok(bytes) = tokio::fs::read(&file_path).await {
        let disp = format!("attachment; filename=\"timesensei_{}.jpg\"", photo_id);
        (
            [
                (header::CONTENT_TYPE, "image/jpeg"),
                (header::CONTENT_DISPOSITION, &disp),
            ],
            bytes,
        )
            .into_response()
    } else {
        (StatusCode::NOT_FOUND, "Image not found").into_response()
    }
}

async fn prune_old_captures_task(captures_dir: PathBuf) {
    loop {
        tokio::time::sleep(Duration::from_secs(1800)).await;
        if let Ok(entries) = std::fs::read_dir(&captures_dir) {
            let mut captures: Vec<(SystemTime, PathBuf)> = entries
                .filter_map(|e| e.ok())
                .filter_map(|e| {
                    let path = e.path();
                    if path.extension().and_then(|s| s.to_str()) == Some("jpg") {
                        let meta = e.metadata().ok()?;
                        let mtime = meta.modified().unwrap_or(SystemTime::UNIX_EPOCH);
                        Some((mtime, path))
                    } else {
                        None
                    }
                })
                .collect();

            let now = SystemTime::now();
            let max_age = Duration::from_secs(config::PHOTO_RETENTION_HOURS * 3600);

            // Prune by age
            for (mtime, path) in &captures {
                if let Ok(elapsed) = now.duration_since(*mtime) {
                    if elapsed > max_age {
                        let _ = std::fs::remove_file(path);
                    }
                }
            }

            // Prune by count ceiling
            captures.sort_by(|a, b| a.0.cmp(&b.0)); // Oldest first
            if captures.len() > config::MAX_CAPTURES_STORED {
                let to_remove = captures.len() - config::MAX_CAPTURES_STORED;
                for (_, path) in captures.iter().take(to_remove) {
                    let _ = std::fs::remove_file(path);
                }
            }
        }
    }
}

pub fn start_sharing_server(port: u16) -> u16 {
    let captures_dir = config::captures_dir();
    let template_path = config::base_dir().join("sharing").join("templates").join("index.html");
    let assets_dir = config::assets_dir();

    let state = Arc::new(ServerState {
        captures_dir: captures_dir.clone(),
        template_path,
    });

    let app = Router::new()
        .route("/", get(handle_root_or_latest))
        .route("/latest", get(handle_root_or_latest))
        .route("/health", get(handle_health))
        .route("/photo/:id", get(handle_view_photo))
        .route("/image/:id", get(handle_get_image))
        .route("/download/:id", get(handle_download_image))
        .nest_service("/assets", ServeDir::new(assets_dir))
        .with_state(state);

    // Find available port starting from `port`
    let mut chosen_port = port;
    let mut listener = None;
    for test_port in port..(port + 20) {
        let addr = SocketAddr::from(([0, 0, 0, 0], test_port));
        if let Ok(l) = std::net::TcpListener::bind(addr) {
            let _ = l.set_nonblocking(true);
            chosen_port = test_port;
            listener = Some(l);
            break;
        }
    }

    if let Some(std_listener) = listener {
        tokio::spawn(async move {
            if let Ok(tokio_listener) = tokio::net::TcpListener::from_std(std_listener) {
                let local_ip = crate::capture::qr::get_local_ip();
                println!("[SharingServer] TimeSensei mobile sharing live at http://{}:{}", local_ip, chosen_port);
                let _ = axum::serve(tokio_listener, app).await;
            }
        });
        tokio::spawn(prune_old_captures_task(captures_dir));
    }

    chosen_port
}
