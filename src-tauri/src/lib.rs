use std::net::TcpListener;
use std::sync::Mutex;
use std::time::Duration;

use tauri::{Emitter, Manager, State};
use tauri_plugin_shell::process::CommandEvent;
use tauri_plugin_shell::ShellExt;

struct SidecarState(Mutex<Option<tauri_plugin_shell::process::CommandChild>>);
struct BackendPortState(Mutex<Option<u16>>);

#[tauri::command]
fn get_backend_port(state: State<'_, BackendPortState>) -> Option<u16> {
  *state.0.lock().unwrap()
}

fn shutdown_sidecar(app_handle: &tauri::AppHandle) {
  let state = app_handle.state::<SidecarState>();
  let mut guard = state.0.lock().unwrap();
  if let Some(child) = guard.take() {
    let _ = child.kill();
  }
}

fn pick_free_port() -> u16 {
  TcpListener::bind(("127.0.0.1", 0))
    .and_then(|l| l.local_addr())
    .map(|a| a.port())
    .unwrap_or(5000)
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
  let context = tauri::generate_context!();

  let app = tauri::Builder::default()
    .manage(SidecarState(Mutex::new(None)))
    .manage(BackendPortState(Mutex::new(None)))
    .plugin(tauri_plugin_shell::init())
    .invoke_handler(tauri::generate_handler![get_backend_port])
    .setup(|app| {
      if cfg!(debug_assertions) {
        app.handle().plugin(
          tauri_plugin_log::Builder::default()
            .level(log::LevelFilter::Info)
            .build(),
        )?;
      }

      let port = pick_free_port();
      *app.state::<BackendPortState>().0.lock().unwrap() = Some(port);
      log::info!("backend port: {}", port);
      let sidecar_command = app
        .shell()
        .sidecar("zhiyiquant-backend")?
        .args(["--host", "127.0.0.1", "--port", &port.to_string()]);

      let (mut rx, child) = sidecar_command.spawn()?;
      *app.state::<SidecarState>().0.lock().unwrap() = Some(child);

      app.emit("zhiyiquant:backend-port", port)?;

      let app_handle = app.handle().clone();
      tauri::async_runtime::spawn(async move {
        while let Some(event) = rx.recv().await {
          match event {
            CommandEvent::Stdout(line) => {
              let _ = app_handle.emit("zhiyiquant:backend-stdout", String::from_utf8_lossy(&line).to_string());
            }
            CommandEvent::Stderr(line) => {
              let _ = app_handle.emit("zhiyiquant:backend-stderr", String::from_utf8_lossy(&line).to_string());
            }
            _ => {}
          }
        }
      });

      let autoclose_ms = std::env::var("ZHIYIQUANT_AUTOCLOSE_MS").ok().and_then(|v| v.parse::<u64>().ok());
      if let Some(ms) = autoclose_ms {
        let app_handle = app.handle().clone();
        std::thread::spawn(move || {
          std::thread::sleep(Duration::from_millis(ms));
          if let Some(w) = app_handle.get_webview_window("main") {
            let _ = w.close();
          }
        });
      }

      Ok(())
    })
    .build(context)
    .expect("error while building tauri application");

  app.run(|app_handle, event| {
    match event {
      tauri::RunEvent::ExitRequested { .. } => {
        shutdown_sidecar(app_handle);
      }
      tauri::RunEvent::Exit => {
        shutdown_sidecar(app_handle);
      }
      _ => {}
    }
  });
}
