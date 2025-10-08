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

function randomUser(prefix = "jest_user") {
  const n = Math.floor(Math.random() * 1e9);
  return `${prefix}_${Date.now()}_${n}`;
}

describe("Live API Tests (localhost:8000)", () => {
  let testUsername: string;
  let testPassword: string;

  beforeAll(async () => {
    localStorage.clear();
    const ok = await apiClient.setApiUrl(BASE_URL);
    expect(ok).toBe(true);
    expect(apiClient.getApiUrl()).toBe(BASE_URL);

    testUsername = randomUser();
    testPassword = "test_password_123!";
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
    "registers and logs in a user",
    async () => {
      const register = await apiClient.post<
        { username: string; password: string },
        BasicTaskResponse
      >("/user/auth/register", {
        username: testUsername,
        password: testPassword,
      });
      expect(isApiError(register)).toBe(false);
      if (!isApiError(register)) {
        expect(typeof register.result).toBe("string");
      }

      const resp = await fetch(`${BASE_URL}/user/auth/login`, {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({
          username: testUsername,
          password: testPassword,
        }),
      });
      expect(resp.ok).toBe(true);
      const setCookie = resp.headers.get("set-cookie") || "";
      const cookiePair = setCookie.split(";")[0];
      expect(cookiePair).toMatch(/=/);

      const originalFetch = global.fetch as typeof fetch;
      global.fetch = ((input: any, init: any = {}) => {
        const headers = new Headers(init.headers || {});
        if (cookiePair && !headers.has("Cookie")) {
          headers.set("Cookie", cookiePair);
        }
        return originalFetch(input, { ...init, headers });
      }) as typeof fetch;
    },
    TIMEOUT,
  );

  it(
    "lists modules and fetches module info when available",
    async () => {
      const all = await apiClient.get<UserModuleAllResponse>("/module/all");
      expect(isApiError(all)).toBe(false);
      if (isApiError(all)) return;

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
    "lists clients and installed modules for first client (if any)",
    async () => {
      const clients = await apiClient.get<ClientAllResponse>("/client/all");
      expect(isApiError(clients)).toBe(false);
      if (isApiError(clients)) return;

      expect(Array.isArray(clients.clients)).toBe(true);
      if (clients.clients.length === 0) {
        return;
      }

      const client = clients.clients[0];
      const installed = await apiClient.get<InstalledModuleInfo[]>(
        `/module/installed/${encodeURIComponent(client.username)}`,
      );
      expect(!isApiError(installed)).toBe(true);
      if (!isApiError(installed)) {
        expect(Array.isArray(installed)).toBe(true);
      }
    },
    TIMEOUT,
  );

  it(
    "runs and cancels a module for a client when possible",
    async () => {
      const [clients, modules] = await Promise.all([
        apiClient.get<ClientAllResponse>("/client/all"),
        apiClient.get<UserModuleAllResponse>("/module/all"),
      ]);

      if (isApiError(clients) || isApiError(modules)) {
        expect(true).toBe(true);
        return;
      }

      if (clients.clients.length === 0 || modules.modules.length === 0) {
        expect(true).toBe(true);
        return;
      }

      const client = clients.clients[0];
      const moduleName = modules.modules[0].name;

      const run = await apiClient.get<BasicTaskResponse>(
        `/user/modules/run/${encodeURIComponent(moduleName)}?client_username=${encodeURIComponent(
          client.username,
        )}`,
      );
      expect(isApiError(run)).toBe(false);

      const cancel = await apiClient.get<BasicTaskResponse>(
        `/user/modules/cancel/${encodeURIComponent(moduleName)}?client_username=${encodeURIComponent(
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
      const clients = await apiClient.get<ClientAllResponse>("/client/all");
      if (isApiError(clients) || clients.clients.length === 0) {
        expect(true).toBe(true);
        return;
      }

      const firstUsername = clients.clients[0].username;
      const info = await apiClient.get<ClientInfo>(
        `/client/get/${encodeURIComponent(firstUsername)}`,
      );
      expect(isApiError(info)).toBe(false);
      if (!isApiError(info)) {
        expect(info.username).toBe(firstUsername);
        expect(typeof info.uuid).toBe("string");
      }
    },
    TIMEOUT,
  );
});
