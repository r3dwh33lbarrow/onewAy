use std::env;
use std::path::{Component, Path, PathBuf};

pub(crate) fn str_to_snake_case(input: &str) -> String {
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

pub(crate) fn title_case_to_camel_case(input: &str) -> String {
    input
        .split_whitespace()
        .map(|word| word.to_lowercase())
        .collect::<Vec<String>>()
        .join("_")
}

pub(crate) fn resolve_current_dir(path: &str) -> String {
    let replaced = path.replace(
        "[CURRENT_DIR]",
        env::current_dir()
            .expect("Failed to get current dir")
            .to_str()
            .unwrap(),
    );

    let p = Path::new(&replaced);

    // Prefer filesystem-aware canonicalization to fully resolve `.` and `..`.
    if let Ok(canon) = std::fs::canonicalize(p) {
        return canon.to_string_lossy().into_owned();
    }

    // Fallback to a logical normalization that removes `.` and processes `..` without touching FS.
    let mut buf = PathBuf::new();
    for comp in p.components() {
        match comp {
            Component::CurDir => {}
            Component::ParentDir => {
                buf.pop();
            }
            other => buf.push(other),
        }
    }

    buf.to_string_lossy().into_owned()
}
