use std::env;

pub fn str_to_snake_case(input: &str) -> String {
    let mut result = String::new();

    for (i, c) in input.chars().enumerate() {
        if c.is_alphanumeric() {
            result.push(c.to_ascii_lowercase());
        } else {
            if i > 0 && !result.ends_with("_") {
                result.push('_');
            }
        }
    }

    result.trim_matches('_').to_string()
}

pub fn title_case_to_camel_case(input: &str) -> String {
    input
        .split_whitespace()
        .map(|word| word.to_lowercase())
        .collect::<Vec<String>>()
        .join("_")
}

pub fn resolve_current_dir(path: &str) -> String {
    path.replace(
        "[CURRENT_DIR]",
        env::current_dir()
            .expect("Failed to get current dir")
            .to_str()
            .unwrap(),
    )
}