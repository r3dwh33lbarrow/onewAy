use std::{io, thread};
use std::io::BufRead;
use std::sync::mpsc;
use std::time::Duration;

fn main() {
    let (tx, rx) = mpsc::channel();

    thread::spawn(move || {
        let stdin = io::stdin();
        let mut line = String::new();
        if stdin.lock().read_line(&mut line).is_ok() {
            let _ = tx.send(line);
        }
    });

    match rx.recv_timeout(Duration::from_secs(3)) {
        Ok(line) => {
            print!("Got it: {}", line);
        }
        Err(_) => {
            panic!("no stdin received");
        }
    }
}
