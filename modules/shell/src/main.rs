use std::io::{self, Write};
use std::process::Command;

fn main() {
    loop {
        print!("> ");
        io::stdout().flush().unwrap();

        let mut input = String::new();
        io::stdin().read_line(&mut input).expect("Failed to read line");

        let input = input.trim();

        if input.is_empty() {
            continue;
        }
        if input == "exit" {
            break;
        }

        let mut parts = input.split_whitespace();
        let cmd = parts.next().unwrap();
        let args: Vec<&str> = parts.collect();

        let output = Command::new(cmd)
            .args(args)
            .output();

        match output {
            Ok(output) => {
                if output.status.success() {
                    let s = String::from_utf8_lossy(&output.stdout);
                    print!("{}", s);
                    io::stdout().flush().ok();
                } else {
                    let s = String::from_utf8_lossy(&output.stderr);
                    eprint!("{}", s);
                    io::stderr().flush().ok();
                }
            }
            Err(e) => eprintln!("Failed to execute '{}': {}", cmd, e),
        }
    }
}
