import { apiClient } from "../apiClient";
import type { BasicTaskResponse } from "../schemas/general";

export async function Login(data: {
  username: string;
  password: string;
}): Promise<boolean> {
  const response = await apiClient.post<typeof data, BasicTaskResponse>(
    "/user/auth/login",
    data,
  );
  return "result" in response;
}

export async function Register(data: {
  username: string;
  password: string;
}): Promise<boolean> {
  const response = await apiClient.post<typeof data, BasicTaskResponse>(
    "/user/auth/register",
    data,
  );
  return "result" in response;
}
