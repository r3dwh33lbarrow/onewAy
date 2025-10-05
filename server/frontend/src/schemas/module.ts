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

export interface InstalledModuleInfo {
  name: string;
  description: string;
  version: string;
  status: string;
}

export interface UploadModuleResponse {
  result: string;
}