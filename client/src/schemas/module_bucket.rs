use serde::{Deserialize, Serialize};

#[derive(Debug, Deserialize, Serialize)]
pub struct BucketData {
    pub(crate) data: String,
}