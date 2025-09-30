import { apiClient, type ApiError } from "../apiClient";
import type { AuthRequest } from "../schemas/authentication.ts";
import type { BasicTaskResponse } from "../schemas/general";

export async function Login(
  data: AuthRequest,
): Promise<BasicTaskResponse | ApiError> {
  return await apiClient.post<typeof data, BasicTaskResponse>(
    "/user/auth/login",
    data,
  );
}

export async function Register(
  data: AuthRequest,
): Promise<BasicTaskResponse | ApiError> {
  return await apiClient.post<typeof data, BasicTaskResponse>(
    "/user/auth/register",
    data,
  );
}
