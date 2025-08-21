import {apiClient} from '../apiClient';
import type {BasicTaskResponse} from "../schemas/general";

export async function Login(data: { username: string, password: string, rememberMe: boolean }): Promise<boolean> {
  const response = await apiClient.post<typeof data, BasicTaskResponse>('/user/auth/login', data);
  return 'result' in response;
}