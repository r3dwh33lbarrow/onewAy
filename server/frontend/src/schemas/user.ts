export interface UserInfoResponse {
  username: string;
  is_admin: boolean;
  last_login: string; // ISO datetime
  created_at: string; // ISO datetime
  avatar_set: boolean;
}

export interface UserUpdateRequest {
  username?: string;
}
