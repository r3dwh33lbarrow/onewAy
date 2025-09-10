use hostname::get;

fn get_hostname() -> String {
    get()
        .ok()
        .and_then(|h| h.into_string().ok())
        .unwrap_or_default()
}