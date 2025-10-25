import type { RefObject } from "react";

import type { TokenResponse } from "./schemas/authentication.ts";
import { useAuthStore } from "./stores/authStore.ts";
import { useRedirectReasonStore } from "./stores/redirectReasonStore.ts";

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
  private userSocket: WebSocket | null = null;
  private userSocketConnecting = false;
  private messageListeners = new Set<(event: MessageEvent) => void>();
  private inflightJsonRequests = new Map<string, Promise<unknown>>();
  private inflightByteRequests = new Map<string, Promise<unknown>>();

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

  private handleApiUrlNotConfigured(): ApiError {
    useRedirectReasonStore
      .getState()
      .setReason("API URL not configured. Please configure your API URL.");
    useAuthStore.getState().clearUser();

    return {
      statusCode: -1,
      message: "API URL not configured. Please set a valid API URL first.",
    };
  }

  private handleUnauthorized(): void {
    useRedirectReasonStore
      .getState()
      .setReason("Your session has expired. Please log in again.");
    useAuthStore.getState().clearUser();
  }

  private async refreshAccessToken(): Promise<boolean> {
    if (!this.apiUrl) {
      return false;
    }

    try {
      const response = await fetch(`${this.apiUrl}/user/auth/refresh`, {
        method: "POST",
        credentials: "include",
      });

      if (!response.ok) {
        return false;
      }

      // Successful refresh returns 200 with no payload.
      return true;
    } catch (error) {
      console.error("Refresh token request failed:", error);
      return false;
    }
  }

  private async handleErrorResponse(response: Response): Promise<ApiError> {
    if (response.status === 401) {
      this.handleUnauthorized();
    }

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

  private createErrorFromException(error: unknown): ApiError {
    return {
      statusCode: -1,
      message:
        error instanceof Error ? error.message : "Unknown error occurred",
    };
  }

  protected async request<T>(
    endpoint: string,
    options: RequestInit = {},
  ): Promise<T | ApiError> {
    if (!this.apiUrl) {
      return this.handleApiUrlNotConfigured();
    }

    try {
      const url = `${this.apiUrl}${endpoint}`;
      const method = (options.method ?? "GET").toUpperCase();
      const headers = {
        ...(options.headers ?? {}),
      } as Record<string, string>;

      const hasContentTypeHeader = Object.keys(headers).some(
        (key) => key.toLowerCase() === "content-type",
      );

      if (typeof options.body === "string" && !hasContentTypeHeader) {
        headers["Content-Type"] = "application/json";
      }

      const init: RequestInit = {
        ...options,
        method,
        headers,
        credentials: "include",
      };

      const cacheKey =
        method === "GET" && !init.body ? `${method}:${url}` : null;

      if (cacheKey && this.inflightJsonRequests.has(cacheKey)) {
        return (await this.inflightJsonRequests.get(cacheKey)!) as T | ApiError;
      }

      const requestPromise = this.executeJsonRequest<T>(url, init);

      if (cacheKey) {
        const wrapped = requestPromise.finally(() => {
          this.inflightJsonRequests.delete(cacheKey);
        });
        this.inflightJsonRequests.set(cacheKey, wrapped);
        return (await wrapped) as T | ApiError;
      }

      return await requestPromise;
    } catch (error) {
      return this.createErrorFromException(error);
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
      return this.handleApiUrlNotConfigured();
    }

    try {
      const url = `${this.apiUrl}${endpoint}`;
      const method = (options.method ?? "GET").toUpperCase();
      const init: RequestInit = {
        ...options,
        method,
        credentials: "include",
      };

      const cacheKey =
        method === "GET" && !init.body ? `${method}:${url}:bytes` : null;

      if (cacheKey && this.inflightByteRequests.has(cacheKey)) {
        return (await this.inflightByteRequests.get(cacheKey)!) as
          | ArrayBuffer
          | ApiError;
      }

      const requestPromise = this.executeBytesRequest(url, init);

      if (cacheKey) {
        const wrapped = requestPromise.finally(() => {
          this.inflightByteRequests.delete(cacheKey);
        });
        this.inflightByteRequests.set(cacheKey, wrapped);
        return (await wrapped) as ArrayBuffer | ApiError;
      }

      return await requestPromise;
    } catch (error) {
      return this.createErrorFromException(error);
    }
  }

  private async executeJsonRequest<T>(
    url: string,
    init: RequestInit,
  ): Promise<T | ApiError> {
    const performFetch = () => fetch(url, init);

    let response = await performFetch();

    if (response.status === 401) {
      const refreshed = await this.refreshAccessToken();
      if (refreshed) {
        response = await performFetch();
      }
    }

    if (response.status === 401) {
      return await this.handleErrorResponse(response);
    }

    if (!response.ok) {
      return await this.handleErrorResponse(response);
    }

    const contentLength = response.headers.get("content-length");
    const contentType = response.headers.get("content-type");

    if (contentLength === "0" || !contentType?.includes("application/json")) {
      return {} as T;
    }

    return (await response.json()) as T;
  }

  private async executeBytesRequest(
    url: string,
    init: RequestInit,
  ): Promise<ArrayBuffer | ApiError> {
    const performFetch = () => fetch(url, init);

    let response = await performFetch();

    if (response.status === 401) {
      const refreshed = await this.refreshAccessToken();
      if (refreshed) {
        response = await performFetch();
      }
    }

    if (response.status === 401) {
      return await this.handleErrorResponse(response);
    }

    if (!response.ok) {
      return await this.handleErrorResponse(response);
    }

    return await response.arrayBuffer();
  }

  public async uploadFolder<T>(
    endpoint: string,
    files: File[],
    method: "PUT" | "POST" = "POST",
  ): Promise<T | ApiError> {
    try {
      const formData = new FormData();
      files.forEach((file) => {
        formData.append("files", file);
      });

      return await this.request<T>(endpoint, {
        method: method,
        body: formData,
        credentials: "include",
      });
    } catch (error) {
      return this.createErrorFromException(error);
    }
  }

  private broadcastMessage(event: MessageEvent): void | ApiError {
    this.messageListeners.forEach((listener) => {
      try {
        listener(event);
      } catch (error) {
        return this.createErrorFromException(error);
      }
    });
  }

  public async startWebSocket(
    sockRef: RefObject<WebSocket | null>,
    onMessage: (event: MessageEvent) => void,
    onError?: (error: ApiError) => void,
  ): Promise<void> {
    this.messageListeners.add(onMessage);

    if (
      this.userSocket &&
      (this.userSocket.readyState === WebSocket.OPEN ||
        this.userSocket.readyState === WebSocket.CONNECTING)
    ) {
      sockRef.current = this.userSocket;
      return;
    }

    if (!this.apiUrl) {
      onError?.({
        statusCode: -1,
        message: "API URL not configured. Please set a valid API URL first.",
      });
      return;
    }

    if (this.userSocketConnecting) {
      const waitForSocket = async (): Promise<void> => {
        if (this.userSocket) {
          sockRef.current = this.userSocket;
          return;
        }
        await new Promise((r) => setTimeout(r, 50));
        return waitForSocket();
      };
      await waitForSocket();
      return;
    }

    try {
      this.userSocketConnecting = true;
      const tokenResponse = await this.post<object, TokenResponse>(
        "/ws-user-token",
        {},
      );
      if (isApiError(tokenResponse)) {
        this.userSocketConnecting = false;
        onError?.(tokenResponse);
        return;
      }

      const wsToken = tokenResponse.access_token;
      const baseUrl = this.apiUrl;
      const url = new URL(baseUrl);
      url.protocol = url.protocol === "https:" ? "wss:" : "ws:";
      url.pathname = "/ws-user";
      url.search = `token=${encodeURIComponent(wsToken)}`;
      const socket = new WebSocket(url.toString());
      this.userSocket = socket;
      sockRef.current = socket;

      socket.addEventListener("message", (event) => {
        this.broadcastMessage(event);
      });

      socket.addEventListener("open", () => {
        this.userSocketConnecting = false;
      });

      socket.addEventListener("error", () => {
        this.userSocketConnecting = false;
      });

      socket.addEventListener("close", () => {
        this.userSocket = null;
        this.messageListeners.clear();
      });
    } catch (error) {
      this.userSocketConnecting = false;
      onError?.(this.createErrorFromException(error));
    }
  }

  public removeWebSocketListener(
    onMessage: (event: MessageEvent) => void,
  ): void {
    this.messageListeners.delete(onMessage);
  }
}

export const apiClient = new ApiClient();
