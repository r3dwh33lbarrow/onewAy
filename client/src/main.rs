mod api_client;
mod logger;
mod schemas;

use crate::api_client::ApiClient;
use crate::schemas::auth::ClientEnrollRequest;
use crate::schemas::BasicTaskResponse;

#[tokio::main]
async fn main() {
    let api_client =
        ApiClient::new("http://127.0.0.1:8000/").expect("failed to initialize ApiClient");
    let mut enroll_data = ClientEnrollRequest::default();
    enroll_data.username = String::from("REDACTED");
    enroll_data.password = String::from("REDACTED");
    enroll_data.client_version = String::from("0.1.0");

    debug!("Sending data...");
    let response = api_client
        .post::<BasicTaskResponse, ClientEnrollRequest>("/client/auth/enroll", &enroll_data)
        .await
        .expect("failed to post /client/auth/enroll");
    println!("{:?}", response);
}
