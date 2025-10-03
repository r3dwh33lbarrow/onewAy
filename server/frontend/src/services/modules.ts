import { apiClient, type ApiError } from "../apiClient";
import type { BasicTaskResponse } from "../schemas/general";

export interface ModuleBasicInfo {
  name: string;
  description: string;
  version: string;
  start: string;
  binaries_platform: string[];
}

export interface UserModuleAllResponse {
  modules: ModuleBasicInfo[];
}

export async function getAllModules(): Promise<
  UserModuleAllResponse | ApiError
> {
  return await apiClient.get<UserModuleAllResponse>("/module/all");
}

export interface InstalledModuleInfo {
  name: string;
  description: string;
  version: string;
  status: string;
}

export async function getInstalledModules(
  clientUsername: string,
): Promise<InstalledModuleInfo[] | ApiError> {
  return await apiClient.get<InstalledModuleInfo[]>(
    `/module/installed/${encodeURIComponent(clientUsername)}`,
  );
}

export interface UploadModuleResponse {
  result: string;
}

export async function uploadModuleFolder(
  files: File[],
): Promise<UploadModuleResponse | ApiError> {
  const apiUrl = apiClient.getApiUrl();
  if (!apiUrl) {
    return {
      statusCode: -1,
      message: "API URL not configured. Please set a valid API URL first.",
    };
  }

  try {
    const formData = new FormData();

    files.forEach((file) => {
      formData.append("files", file);
    });

    const url = `${apiUrl}/module/upload`;
    console.log("API Request:", url);
    console.log(
      "Uploading files:",
      files.map((f) => f.webkitRelativePath || f.name),
    );

    const response = await fetch(url, {
      method: "PUT",
      body: formData,
      credentials: "include",
    });

    if (!response.ok) {
      let errorMessage = response.statusText || `HTTP ${response.status} error`;
      try {
        const errorData = await response.json();
        console.log("Error response data:", errorData);
        if (errorData.detail) {
          errorMessage = Array.isArray(errorData.detail)
            ? errorData.detail.join(", ")
            : errorData.detail;
        } else if (errorData.message) {
          errorMessage = errorData.message;
        } else if (typeof errorData === "string") {
          errorMessage = errorData;
        } else {
          errorMessage = JSON.stringify(errorData);
        }
      } catch (e) {
        console.log("Failed to parse error response:", e);
      }

      return {
        statusCode: response.status,
        message: errorMessage,
      };
    }

    return (await response.json()) as UploadModuleResponse;
  } catch (error) {
    return {
      statusCode: -1,
      message:
        error instanceof Error ? error.message : "Unknown error occurred",
    };
  }
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
