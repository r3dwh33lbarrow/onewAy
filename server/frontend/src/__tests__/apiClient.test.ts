import { apiClient, isApiError } from "../apiClient";
import type { ClientAllResponse, ClientInfo } from "../schemas/client";
import type { RootResponse, BasicTaskResponse } from "../schemas/general";
import type {
  UserModuleAllResponse,
  ModuleInfo,
  InstalledModuleInfo,
} from "../schemas/module";

const BASE_URL = "http://localhost:8000";
const TIMEOUT = 30000;

describe("Live API Tests (localhost:8000)", () => {
  beforeAll(async () => {
    localStorage.clear();
    const ok = await apiClient.setApiUrl(BASE_URL);
    expect(ok).toBe(true);
    expect(apiClient.getApiUrl()).toBe(BASE_URL);
  }, TIMEOUT);

  it(
    "root endpoint responds with API banner",
    async () => {
      const res = await fetch(BASE_URL, { credentials: "include" });
      expect(res.ok).toBe(true);
      const data = (await res.json()) as RootResponse;
      expect(data.message).toBe("onewAy API");
    },
    TIMEOUT,
  );

  it(
    "lists modules when authenticated",
    async () => {
      const all = await apiClient.get<UserModuleAllResponse>("/module/all");
      // May be unauthorized if not logged in, which is expected
      if (isApiError(all)) {
        expect([401, 403]).toContain(all.statusCode);
        return;
      }

      expect(Array.isArray(all.modules)).toBe(true);
      if (all.modules.length > 0) {
        const name = all.modules[0].name;
        const mod = await apiClient.get<ModuleInfo>(`/module/get/${name}`);
        expect(isApiError(mod)).toBe(false);
        if (!isApiError(mod)) {
          expect(mod.name).toBe(name);
          expect(typeof mod.version).toBe("string");
        }
      }
    },
    TIMEOUT,
  );

  it(
    "lists clients when authenticated (if any)",
    async () => {
      const clients = await apiClient.get<ClientAllResponse>("/client/get-all");
      if (isApiError(clients)) {
        // In CI without authentication, the API will reject the request
        expect([401, 403, 404]).toContain(clients.statusCode);
        return;
      }

      expect(Array.isArray(clients.clients)).toBe(true);
      if (clients.clients.length === 0) {
        return;
      }

      const client = clients.clients[0];
      const installed = await apiClient.get<{ all_installed: InstalledModuleInfo[] }>(
        `/module/installed/${encodeURIComponent(client.username)}`,
      );
      expect(!isApiError(installed)).toBe(true);
      if (!isApiError(installed)) {
        expect(Array.isArray(installed.all_installed)).toBe(true);
      }
    },
    TIMEOUT,
  );

  it(
    "runs and cancels a module for a client when possible",
    async () => {
      const [clients, modules] = await Promise.all([
        apiClient.get<ClientAllResponse>("/client/get-all"),
        apiClient.get<UserModuleAllResponse>("/module/all"),
      ]);

      if (isApiError(clients)) {
        expect([401, 403, 404]).toContain(clients.statusCode);
        return;
      }
      if (isApiError(modules)) {
        expect(modules.statusCode).toBeGreaterThanOrEqual(400);
        return;
      }

      if (clients.clients.length === 0 || modules.modules.length === 0) {
        expect(true).toBe(true);
        return;
      }

      const client = clients.clients[0];
      const moduleName = modules.modules[0].name;

      const run = await apiClient.get<BasicTaskResponse>(
        `/module/run/${encodeURIComponent(moduleName)}?client_username=${encodeURIComponent(
          client.username,
        )}`,
      );
      // May fail if client is offline or module not installed
      if (isApiError(run)) {
        expect(run.statusCode).toBeGreaterThanOrEqual(400);
        return;
      }

      const cancel = await apiClient.get<BasicTaskResponse>(
        `/module/cancel/${encodeURIComponent(moduleName)}?client_username=${encodeURIComponent(
          client.username,
        )}`,
      );
      expect(isApiError(cancel)).toBe(false);
    },
    TIMEOUT,
  );

  it(
    "fetches a single client's full info when present",
    async () => {
      const clients = await apiClient.get<ClientAllResponse>("/client/get-all");
      if (isApiError(clients)) {
        expect([401, 403, 404]).toContain(clients.statusCode);
        return;
      }
      if (clients.clients.length === 0) {
        return;
      }

      const firstUsername = clients.clients[0].username;
      const info = await apiClient.get<ClientInfo>(
        `/client/action/${encodeURIComponent(firstUsername)}`,
      );
      expect(isApiError(info)).toBe(false);
      if (!isApiError(info)) {
        expect(info.username).toBe(firstUsername);
        expect(typeof info.uuid).toBe("string");
      }
    },
    TIMEOUT,
  );

  it(
    "handles API errors gracefully",
    async () => {
      const result = await apiClient.get("/nonexistent-endpoint");
      expect(isApiError(result)).toBe(true);
      if (isApiError(result)) {
        expect(result.statusCode).toBe(404);
      }
    },
    TIMEOUT,
  );

  it(
    "isApiError correctly identifies errors",
    () => {
      const error = {
        statusCode: 404,
        message: "Not Found",
        detail: "Resource not found",
      };
      expect(isApiError(error)).toBe(true);

      const success = { result: "success" };
      expect(isApiError(success)).toBe(false);
    },
  );
});
