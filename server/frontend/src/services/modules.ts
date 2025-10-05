import { apiClient, type ApiError } from "../apiClient";
import type { BasicTaskResponse } from "../schemas/general";
import type {
  InstalledModuleInfo,
  UploadModuleResponse,
  UserModuleAllResponse,
} from "../schemas/module.ts";

export async function getAllModules(): Promise<
  UserModuleAllResponse | ApiError
> {
  return await apiClient.get<UserModuleAllResponse>("/module/all");
}

export async function getInstalledModules(
  clientUsername: string,
): Promise<InstalledModuleInfo[] | ApiError> {
  return await apiClient.get<InstalledModuleInfo[]>(
    `/module/installed/${encodeURIComponent(clientUsername)}`,
  );
}

export async function uploadModuleFolder(
  files: File[],
): Promise<UploadModuleResponse | ApiError> {
  return await apiClient.uploadFolder<UploadModuleResponse>(
    "/module/upload",
    files,
    "PUT",
  );
}

export async function runModule(
  clientUsername: string,
  moduleName: string,
): Promise<BasicTaskResponse | ApiError> {
  return await apiClient.get<BasicTaskResponse>(
    `/user/modules/run/${encodeURIComponent(moduleName)}?client_username=${encodeURIComponent(clientUsername)}`,
  );
}

export async function cancelModule(
  clientUsername: string,
  moduleName: string,
): Promise<BasicTaskResponse | ApiError> {
  return await apiClient.get<BasicTaskResponse>(
    `/user/modules/cancel/${encodeURIComponent(moduleName)}?client_username=${encodeURIComponent(clientUsername)}`,
  );
}
