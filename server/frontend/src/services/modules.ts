import {apiClient, type ApiError} from "../apiClient";

export interface ModuleBasicInfo {
  name: string;
  version: string;
  binaries_platform: string[];
}

export interface UserModuleAllResponse {
  modules: ModuleBasicInfo[];
}

export async function getAllModules(): Promise<UserModuleAllResponse | ApiError> {
  return await apiClient.get<UserModuleAllResponse>("/user/modules/all");
}