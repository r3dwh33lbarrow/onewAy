use client::schemas::ApiError;

#[test]
fn test_api_error_display_format() {
    let e = ApiError {
        status_code: 404,
        detail: "Not Found".to_string(),
    };
    let s = format!("{}", e);
    assert!(s.contains("API Error 404"));
    assert!(s.contains("Not Found"));
}
