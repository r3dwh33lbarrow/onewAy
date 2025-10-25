use chrono::Local;

fn get_current_date_time() -> String {
    let now = Local::now();
    now.format("%m/%d/%Y %H:%M:%S").to_string()
}

fn main() {
    // Track network activity
    println!("{}", get_current_date_time());
}
