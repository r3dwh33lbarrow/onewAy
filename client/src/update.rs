use crate::http::api_client::ApiClient;
use anyhow::Result;
use std::env;
use std::process::{Command, exit};

pub async fn get_update(api_client: &ApiClient) -> Result<()> {
    let current_binary = env::current_exe()?;
    let binary_directory = current_binary.parent().unwrap();
    let tmp_path = binary_directory.join("temp_update_bin");

    api_client.get_file("/client/update", &tmp_path).await?;

    Command::new(&tmp_path).args(env::args().skip(1)).spawn()?;

    exit(0);
}
