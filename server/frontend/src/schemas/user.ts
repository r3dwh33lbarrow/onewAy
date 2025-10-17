export interface UserInfoResponse {
  username: string;
  is_admin: boolean;
  last_login: string;
  created_at: string;
  avatar_set: boolean;
}

export interface UserUpdateRequest {
  username?: string;
}
