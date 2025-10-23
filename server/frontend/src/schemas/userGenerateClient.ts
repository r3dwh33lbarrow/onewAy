export interface VerifyRustResponse {
  rust_installed: boolean;
  cargo_installed: boolean;
  windows_target_installed: boolean;
  mac_target_installed: boolean;
  linux_target_installed: boolean;
}
