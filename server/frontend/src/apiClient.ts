export interface ApiError {
  statusCode: number;
  message: string;
}

class ApiClient {
  private apiUrl: string | undefined;

  public async setApiUrl(url: string): Promise<boolean> {
    url = url.trim().replace(/\/+$/, '');
    let validUrl = false;

    try {
      const response = await fetch(`${url}`, {
        credentials: 'include'
      });
      const data = await response.json();

      if (data.message === 'onewAy API') {
        validUrl = true;
      }
    } catch { /* empty */ }

    if (validUrl) {
      this.apiUrl = url;
      return true;
    } else {
      return false;
    }
  }

  protected async request<T>(endpoint: string, options: RequestInit = {}): Promise<T | ApiError> {
    try {
      const url = `${this.apiUrl}${endpoint}`;
      const response = await fetch(url, {
        headers: {
          ...(options.body && { 'Content-Type': 'application/json' }),
          ...options.headers,
        },
        credentials: 'include',
        ...options,
      });

      if (!response.ok) {
        return {
          statusCode: response.status,
          message: response.statusText,
        };
      }

      return await response.json() as T;
    } catch (error) {
      return {
        statusCode: -1,
        message: (error as Error).message,
      };
    }
  }

  public async get<T>(endpoint: string): Promise<T | ApiError> {
    return this.request<T>(endpoint, { method: 'GET' });
  }

  public async post<TRequest, TResponse>(endpoint: string, data: TRequest): Promise<TResponse | ApiError> {
    return this.request<TResponse>(endpoint, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }
}

export const apiClient = new ApiClient();