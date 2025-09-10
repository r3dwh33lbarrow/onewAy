import {apiClient, type ApiError} from "../apiClient";

export interface ModuleBasicInfo {
  name: string;
  description: string;
  version: string;
  binaries_platform: string[];
}

export interface UserModuleAllResponse {
  modules: ModuleBasicInfo[];
}

export async function getAllModules(): Promise<UserModuleAllResponse | ApiError> {
  return await apiClient.get<UserModuleAllResponse>("/user/modules/all");
}

export interface UploadModuleResponse {
  result: string;
}

export async function uploadModule(devName: string, file: File): Promise<UploadModuleResponse | ApiError> {
  // Handle file upload manually since apiClient doesn't support FormData properly
  const apiUrl = apiClient.getApiUrl();
  if (!apiUrl) {
    return {
      statusCode: -1,
      message: 'API URL not configured. Please set a valid API URL first.',
    };
  }

  try {
    const formData = new FormData();
    formData.append('file', file);

    // dev_name should be a query parameter, not form data
    const url = `${apiUrl}/user/modules/upload?dev_name=${encodeURIComponent(devName)}`;
    console.log('API Request:', url);

    const response = await fetch(url, {
      method: 'POST',
      body: formData,
      credentials: 'include',
      // Don't set Content-Type header - let browser set it with boundary for multipart/form-data
    });

    if (!response.ok) {
      let errorMessage = response.statusText || `HTTP ${response.status} error`;
      try {
        const errorData = await response.json();
        console.log('Error response data:', errorData);
        if (errorData.detail) {
          errorMessage = Array.isArray(errorData.detail) ? errorData.detail.join(', ') : errorData.detail;
        } else if (errorData.message) {
          errorMessage = errorData.message;
        } else if (typeof errorData === 'string') {
          errorMessage = errorData;
        } else {
          errorMessage = JSON.stringify(errorData);
        }
      } catch (e) {
        console.log('Failed to parse error response:', e);
        // If we can't parse the error response, use the status text
      }

      return {
        statusCode: response.status,
        message: errorMessage,
      };
    }

    return await response.json() as UploadModuleResponse;
  } catch (error) {
    return {
      statusCode: -1,
      message: error instanceof Error ? error.message : 'Unknown error occurred',
    };
  }
}

export async function uploadModuleFolder(files: File[]): Promise<UploadModuleResponse | ApiError> {
  // Handle multiple file upload for folder-based modules
  const apiUrl = apiClient.getApiUrl();
  if (!apiUrl) {
    return {
      statusCode: -1,
      message: 'API URL not configured. Please set a valid API URL first.',
    };
  }

  try {
    const formData = new FormData();

    // Add all files to the form data
    files.forEach(file => {
      formData.append('files', file);
    });

    const url = `${apiUrl}/user/modules/upload`;
    console.log('API Request:', url);
    console.log('Uploading files:', files.map(f => f.webkitRelativePath || f.name));

    const response = await fetch(url, {
      method: 'POST',
      body: formData,
      credentials: 'include',
      // Don't set Content-Type header - let browser set it with boundary for multipart/form-data
    });

    if (!response.ok) {
      let errorMessage = response.statusText || `HTTP ${response.status} error`;
      try {
        const errorData = await response.json();
        console.log('Error response data:', errorData);
        if (errorData.detail) {
          errorMessage = Array.isArray(errorData.detail) ? errorData.detail.join(', ') : errorData.detail;
        } else if (errorData.message) {
          errorMessage = errorData.message;
        } else if (typeof errorData === 'string') {
          errorMessage = errorData;
        } else {
          errorMessage = JSON.stringify(errorData);
        }
      } catch (e) {
        console.log('Failed to parse error response:', e);
        // If we can't parse the error response, use the status text
      }

      return {
        statusCode: response.status,
        message: errorMessage,
      };
    }

    return await response.json() as UploadModuleResponse;
  } catch (error) {
    return {
      statusCode: -1,
      message: error instanceof Error ? error.message : 'Unknown error occurred',
    };
  }
}
