export interface ApiError {
  statusCode: number;
  message: string;
  detail?: string;
}

export function isApiError(obj: unknown): obj is ApiError {
  return (
    typeof obj === "object" &&
    obj !== null &&
    "statusCode" in obj &&
    "message" in obj
  );
}

class ApiClient {
  private apiUrl: string | undefined;

  public constructor() {
    const apiUrl = localStorage.getItem("apiUrl");
    if (apiUrl) {
      this.apiUrl = apiUrl;
      this.validateAndSetUrl(apiUrl).catch((_) => {});
    }
  }

  private async validateAndSetUrl(url: string): Promise<void> {
    const isValid = await this.validateApiUrl(url);
    if (!isValid) {
      this.apiUrl = undefined;
      localStorage.removeItem("apiUrl");
    }
  }

  public async setApiUrl(url: string): Promise<boolean> {
    const trimmedUrl = url.trim().replace(/\/+$/, "");
    const isValid = await this.validateApiUrl(trimmedUrl);

    if (isValid) {
      this.apiUrl = trimmedUrl;
      localStorage.setItem("apiUrl", trimmedUrl);
      return true;
    } else {
      this.apiUrl = undefined;
      localStorage.removeItem("apiUrl");
      return false;
    }
  }

  private async validateApiUrl(url: string): Promise<boolean> {
    try {
      const response = await fetch(url, {
        credentials: "include",
      });

      if (!response.ok) {
        return false;
      }

      const contentType = response.headers.get("content-type");
      if (!contentType?.includes("application/json")) {
        return false;
      }

      const data = await response.json();
      return data.message === "onewAy API";
    } catch {
      return false;
    }
  }
  public getApiUrl(): string | undefined {
    return this.apiUrl;
  }

  protected async request<T>(
    endpoint: string,
    options: RequestInit = {},
  ): Promise<T | ApiError> {
    if (!this.apiUrl) {
      return {
        statusCode: -1,
        message: "API URL not configured. Please set a valid API URL first.",
      };
    }

    try {
      const url = `${this.apiUrl}${endpoint}`;

      const response = await fetch(url, {
        headers: {
          ...(options.body && { "Content-Type": "application/json" }),
          ...options.headers,
        },
        credentials: "include",
        ...options,
      });

      if (!response.ok) {
        try {
          const errorData = await response.json();
          return {
            statusCode: response.status,
            message: response.statusText || `HTTP ${response.status} error`,
            detail: errorData.detail || undefined,
          };
        } catch {
          return {
            statusCode: response.status,
            message: response.statusText || `HTTP ${response.status} error`,
          };
        }
      }

      const contentLength = response.headers.get("content-length");
      const contentType = response.headers.get("content-type");

      if (contentLength === "0" || !contentType?.includes("application/json")) {
        return {} as T;
      }

      return (await response.json()) as T;
    } catch (error) {
      return {
        statusCode: -1,
        message:
          error instanceof Error ? error.message : "Unknown error occurred",
      };
    }
  }

  public async get<T>(endpoint: string): Promise<T | ApiError> {
    return this.request<T>(endpoint, { method: "GET" });
  }

  public async post<TRequest, TResponse>(
    endpoint: string,
    data: TRequest,
  ): Promise<TResponse | ApiError> {
    return this.request<TResponse>(endpoint, {
      method: "POST",
      body: JSON.stringify(data),
    });
  }

  public async put<TRequest, TResponse>(
    endpoint: string,
    data: TRequest,
  ): Promise<TResponse | ApiError> {
    return this.request<TResponse>(endpoint, {
      method: "PUT",
      body: JSON.stringify(data),
    });
  }

  public async delete<T>(endpoint: string): Promise<T | ApiError> {
    return this.request<T>(endpoint, { method: "DELETE" });
  }

  public async requestBytes(
    endpoint: string,
    options: RequestInit = {},
  ): Promise<ArrayBuffer | ApiError> {
    if (!this.apiUrl) {
      return {
        statusCode: -1,
        message: "API URL not configured. Please set a valid API URL first.",
      };
    }

    try {
      const url = `${this.apiUrl}${endpoint}`;
      const response = await fetch(url, {
        headers: {
          ...options.headers,
        },
        credentials: "include",
        ...options,
      });

      if (!response.ok) {
        try {
          const errorData = await response.json();
          return {
            statusCode: response.status,
            message: response.statusText || `HTTP ${response.status} error`,
            detail: errorData.detail || undefined,
          };
        } catch {
          return {
            statusCode: response.status,
            message: response.statusText || `HTTP ${response.status} error`,
          };
        }
      }

      return await response.arrayBuffer();
    } catch (error) {
      return {
        statusCode: -1,
        message:
          error instanceof Error ? error.message : "Unknown error occurred",
      };
    }
  }
}

export const apiClient = new ApiClient();
