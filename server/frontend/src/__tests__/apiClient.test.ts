import { apiClient } from "../apiClient";
import type {RootResponse, BasicTaskResponse} from "../schemas/general.ts";

interface UserRegisterRequest {
  username: string;
  password: string;
}

interface UserLoginRequest {
  username: string;
  password: string;
}

const API_URL = "http://localhost:8000/";
const TIMEOUT = 10000;

describe('ApiClient - Live API Tests', () => {
  beforeAll(async () => {
    console.log(`Testing against API: ${API_URL}`);
  }, TIMEOUT);

  describe('setApiUrl', () => {
    it('should return true for a valid API URL', async () => {
      const result = await apiClient.setApiUrl(API_URL);
      expect(result).toEqual(true);
    }, TIMEOUT);

    it('should return false for invalid API URL', async () => {
      const result = await apiClient.setApiUrl('http://localhost:9999');

      expect(result).toBe(false);
    }, TIMEOUT);

    it('should return false for malformed URL', async () => {
      const result = await apiClient.setApiUrl('not-a-valid-url');

      expect(result).toBe(false);
    }, TIMEOUT);
  });

  describe('request methods with live API', () => {
    beforeEach(async () => {
      const isValid = await apiClient.setApiUrl(API_URL);
      expect(isValid).toBe(true);
    }, TIMEOUT);

    describe('GET requests', () => {
      it('should successfully make a GET request to root endpoint', async () => {
        const response = await apiClient.get<RootResponse>('');
        expect(response).toHaveProperty('message', 'onewAy API');
      }, TIMEOUT);

      it('should return an error for a non-existent endpoint', async () => {
        const response = await apiClient.get<RootResponse>('/non-existent-endpoint');
        expect(response).toHaveProperty('statusCode', 404);
      }, TIMEOUT);
    });

    describe('POST requests', () => {
      const testUser = {
        username: `testuser_${Date.now()}`,
        password: 'testpassword123'
      };

      describe('User Registration', () => {
        it('should successfully register a new user', async () => {
          const response = await apiClient.post<UserRegisterRequest, BasicTaskResponse>('/user/auth/register', testUser);
          expect(response).toHaveProperty('result', 'success');
        }, TIMEOUT);

        it('should return 409 error for duplicate username', async () => {
          // First registration
          await apiClient.post<UserRegisterRequest, BasicTaskResponse>('/user/auth/register', testUser);

          // Second registration with same username should fail
          const response = await apiClient.post<UserRegisterRequest, any>('/user/auth/register', testUser);
          expect(response).toHaveProperty('statusCode', 409);
          expect(response).toHaveProperty('message', 'Conflict');
        }, TIMEOUT);

        it('should return error for missing username', async () => {
          const invalidUser = { password: 'testpassword123' };
          const response = await apiClient.post<any, any>('/user/auth/register', invalidUser);
          expect(response).toHaveProperty('statusCode', 422);
        }, TIMEOUT);

        it('should return error for missing password', async () => {
          const invalidUser = { username: 'testuser' };
          const response = await apiClient.post<any, any>('/user/auth/register', invalidUser);
          expect(response).toHaveProperty('statusCode', 422);
        }, TIMEOUT);
      });

      describe('User Login', () => {
        const loginUser = {
          username: `loginuser_${Date.now()}`,
          password: 'loginpassword123'
        };

        beforeEach(async () => {
          // Create user before each login test
          await apiClient.post<UserRegisterRequest, BasicTaskResponse>('/user/auth/register', loginUser);
        });

        it('should successfully login with valid credentials', async () => {
          const response = await apiClient.post<UserLoginRequest, BasicTaskResponse>('/user/auth/login', loginUser);
          expect(response).toHaveProperty('result', 'success');
        }, TIMEOUT);

        it('should return 401 error for invalid username', async () => {
          const invalidUser = {
            username: 'nonexistentuser',
            password: loginUser.password
          };
          const response = await apiClient.post<UserLoginRequest, any>('/user/auth/login', invalidUser);
          expect(response).toHaveProperty('statusCode', 401);
          expect(response).toHaveProperty('message', 'Unauthorized');
        }, TIMEOUT);

        it('should return 401 error for invalid password', async () => {
          const invalidUser = {
            username: loginUser.username,
            password: 'wrongpassword'
          };
          const response = await apiClient.post<UserLoginRequest, any>('/user/auth/login', invalidUser);
          expect(response).toHaveProperty('statusCode', 401);
          expect(response).toHaveProperty('message', 'Unauthorized');
        }, TIMEOUT);

        it('should return error for missing username', async () => {
          const invalidUser = { password: 'testpassword123' };
          const response = await apiClient.post<any, any>('/user/auth/login', invalidUser);
          expect(response).toHaveProperty('statusCode', 422);
        }, TIMEOUT);

        it('should return error for missing password', async () => {
          const invalidUser = { username: 'testuser' };
          const response = await apiClient.post<any, any>('/user/auth/login', invalidUser);
          expect(response).toHaveProperty('statusCode', 422);
        }, TIMEOUT);
      });

      describe('User Logout', () => {
        it('should successfully logout user', async () => {
          const response = await apiClient.post<{}, BasicTaskResponse>('/user/auth/logout', {});
          expect(response).toHaveProperty('result', 'success');
        }, TIMEOUT);

        it('should logout even without being logged in', async () => {
          const response = await apiClient.post<{}, BasicTaskResponse>('/user/auth/logout', {});
          expect(response).toHaveProperty('result', 'success');
        }, TIMEOUT);
      });

      describe('Authentication Flow', () => {
        const flowUser = {
          username: `flowuser_${Date.now()}`,
          password: 'flowpassword123'
        };

        it('should complete full authentication flow: register -> login -> logout', async () => {
          // Register
          const registerResponse = await apiClient.post<UserRegisterRequest, BasicTaskResponse>('/user/auth/register', flowUser);
          expect(registerResponse).toHaveProperty('result', 'success');

          // Login
          const loginResponse = await apiClient.post<UserLoginRequest, BasicTaskResponse>('/user/auth/login', flowUser);
          expect(loginResponse).toHaveProperty('result', 'success');

          // Logout
          const logoutResponse = await apiClient.post<{}, BasicTaskResponse>('/user/auth/logout', {});
          expect(logoutResponse).toHaveProperty('result', 'success');
        }, TIMEOUT);
      });

      describe('Error Handling', () => {
        it('should handle malformed JSON in request body', async () => {
          // This test depends on how your apiClient handles malformed requests
          // You might need to adjust based on your implementation
          const response = await apiClient.post<any, any>('/user/auth/register', 'invalid-json');
          expect(response).toHaveProperty('statusCode');
          expect([400, 422]).toContain((response as any).statusCode);
        }, TIMEOUT);

        it('should return 404 for non-existent auth endpoint', async () => {
          const response = await apiClient.post<{}, any>('/user/auth/nonexistent', {});
          expect(response).toHaveProperty('statusCode', 404);
        }, TIMEOUT);
      });
    });
  });
});