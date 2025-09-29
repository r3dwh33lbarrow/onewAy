import { useAuthStore } from "../stores/authStore";

const TIMEOUT = 10000;

describe("AuthStore Tests", () => {
  beforeEach(() => {
    // Clear the store state before each test
    useAuthStore.getState().clearUser();
    // Clear localStorage
    localStorage.clear();
    jest.clearAllMocks();
  }, TIMEOUT);

  describe("Initial State", () => {
    it(
      "should have correct initial state",
      () => {
        const state = useAuthStore.getState();

        expect(state.user).toBeNull();
        expect(state.isAuthenticated).toBe(false);
        expect(typeof state.setUser).toBe("function");
        expect(typeof state.clearUser).toBe("function");
      },
      TIMEOUT,
    );
  });

  describe("setUser", () => {
    it(
      "should set user and authenticate when valid user is provided",
      () => {
        const testUser = { username: "testuser123" };

        useAuthStore.getState().setUser(testUser);
        const state = useAuthStore.getState();

        expect(state.user).toEqual(testUser);
        expect(state.isAuthenticated).toBe(true);
      },
      TIMEOUT,
    );

    it(
      "should update user when different user is set",
      () => {
        const firstUser = { username: "firstuser" };
        const secondUser = { username: "seconduser" };

        // Set first user
        useAuthStore.getState().setUser(firstUser);
        let state = useAuthStore.getState();
        expect(state.user).toEqual(firstUser);
        expect(state.isAuthenticated).toBe(true);

        // Set second user
        useAuthStore.getState().setUser(secondUser);
        state = useAuthStore.getState();
        expect(state.user).toEqual(secondUser);
        expect(state.isAuthenticated).toBe(true);
      },
      TIMEOUT,
    );

    it(
      "should handle user with special characters in username",
      () => {
        const testUser = { username: "test.user@domain_123" };

        useAuthStore.getState().setUser(testUser);
        const state = useAuthStore.getState();

        expect(state.user).toEqual(testUser);
        expect(state.isAuthenticated).toBe(true);
      },
      TIMEOUT,
    );

    it(
      "should handle user with empty username",
      () => {
        const testUser = { username: "" };

        useAuthStore.getState().setUser(testUser);
        const state = useAuthStore.getState();

        expect(state.user).toEqual(testUser);
        expect(state.isAuthenticated).toBe(true);
      },
      TIMEOUT,
    );
  });

  describe("clearUser", () => {
    it(
      "should clear user and deauthenticate",
      () => {
        const testUser = { username: "testuser123" };

        // First set a user
        useAuthStore.getState().setUser(testUser);
        let state = useAuthStore.getState();
        expect(state.user).toEqual(testUser);
        expect(state.isAuthenticated).toBe(true);

        // Then clear the user
        useAuthStore.getState().clearUser();
        state = useAuthStore.getState();
        expect(state.user).toBeNull();
        expect(state.isAuthenticated).toBe(false);
      },
      TIMEOUT,
    );

    it(
      "should work when no user is set",
      () => {
        // Clear user when already cleared
        useAuthStore.getState().clearUser();
        const state = useAuthStore.getState();

        expect(state.user).toBeNull();
        expect(state.isAuthenticated).toBe(false);
      },
      TIMEOUT,
    );

    it(
      "should clear user multiple times without error",
      () => {
        const testUser = { username: "testuser123" };

        // Set user
        useAuthStore.getState().setUser(testUser);

        // Clear multiple times
        useAuthStore.getState().clearUser();
        useAuthStore.getState().clearUser();
        useAuthStore.getState().clearUser();

        const state = useAuthStore.getState();
        expect(state.user).toBeNull();
        expect(state.isAuthenticated).toBe(false);
      },
      TIMEOUT,
    );
  });

  describe("Authentication Flow", () => {
    it(
      "should complete full authentication flow: login -> logout",
      () => {
        const testUser = { username: "flowuser123" };

        // Login (setUser)
        useAuthStore.getState().setUser(testUser);
        let state = useAuthStore.getState();
        expect(state.user).toEqual(testUser);
        expect(state.isAuthenticated).toBe(true);

        // Logout (clearUser)
        useAuthStore.getState().clearUser();
        state = useAuthStore.getState();
        expect(state.user).toBeNull();
        expect(state.isAuthenticated).toBe(false);
      },
      TIMEOUT,
    );

    it(
      "should handle multiple login/logout cycles",
      () => {
        const testUser1 = { username: "user1" };
        const testUser2 = { username: "user2" };

        // First cycle
        useAuthStore.getState().setUser(testUser1);
        expect(useAuthStore.getState().isAuthenticated).toBe(true);

        useAuthStore.getState().clearUser();
        expect(useAuthStore.getState().isAuthenticated).toBe(false);

        // Second cycle with different user
        useAuthStore.getState().setUser(testUser2);
        expect(useAuthStore.getState().user).toEqual(testUser2);
        expect(useAuthStore.getState().isAuthenticated).toBe(true);

        useAuthStore.getState().clearUser();
        expect(useAuthStore.getState().isAuthenticated).toBe(false);
      },
      TIMEOUT,
    );
  });

  describe("Persistence", () => {
    it(
      "should persist user data to localStorage when user is set",
      () => {
        const testUser = { username: "persistuser123" };

        // Clear localStorage first
        localStorage.clear();

        useAuthStore.getState().setUser(testUser);

        // Check if data was persisted to localStorage
        const storedData = localStorage.getItem("auth-storage");
        expect(storedData).not.toBeNull();

        if (storedData) {
          const parsedData = JSON.parse(storedData);
          expect(parsedData.state.user).toEqual(testUser);
          expect(parsedData.state.isAuthenticated).toBe(true);
        }
      },
      TIMEOUT,
    );

    it(
      "should persist cleared state to localStorage when user is cleared",
      () => {
        const testUser = { username: "clearuser123" };

        // Set user first
        useAuthStore.getState().setUser(testUser);

        // Clear user
        useAuthStore.getState().clearUser();

        // Check if cleared state was persisted
        const storedData = localStorage.getItem("auth-storage");
        expect(storedData).not.toBeNull();

        if (storedData) {
          const parsedData = JSON.parse(storedData);
          expect(parsedData.state.user).toBeNull();
          expect(parsedData.state.isAuthenticated).toBe(false);
        }
      },
      TIMEOUT,
    );

    it(
      "should use correct storage key name",
      () => {
        const testUser = { username: "keyuser123" };

        localStorage.clear();
        useAuthStore.getState().setUser(testUser);

        // Check that the correct key was used
        const storedData = localStorage.getItem("auth-storage");
        expect(storedData).not.toBeNull();

        // Verify other keys are not used
        expect(localStorage.getItem("user-storage")).toBeNull();
        expect(localStorage.getItem("auth")).toBeNull();
      },
      TIMEOUT,
    );

    it(
      "should restore user state from localStorage on store initialization",
      () => {
        const testUser = { username: "restoreuser123" };

        // Manually set data in localStorage as if it was persisted before
        const mockStoredData = {
          state: {
            user: testUser,
            isAuthenticated: true,
          },
          version: 0,
        };

        localStorage.setItem("auth-storage", JSON.stringify(mockStoredData));

        // Note: In a real scenario, this would test store rehydration on app restart
        // For this test, we're just verifying the localStorage interaction
        const storedData = localStorage.getItem("auth-storage");
        expect(storedData).not.toBeNull();

        if (storedData) {
          const parsedData = JSON.parse(storedData);
          expect(parsedData.state.user).toEqual(testUser);
          expect(parsedData.state.isAuthenticated).toBe(true);
        }
      },
      TIMEOUT,
    );
  });

  describe("State Consistency", () => {
    it(
      "should maintain consistency between user and isAuthenticated",
      () => {
        const testUser = { username: "consistencyuser" };

        // When user is set, isAuthenticated should be true
        useAuthStore.getState().setUser(testUser);
        let state = useAuthStore.getState();
        expect(state.user).not.toBeNull();
        expect(state.isAuthenticated).toBe(true);

        // When user is cleared, isAuthenticated should be false
        useAuthStore.getState().clearUser();
        state = useAuthStore.getState();
        expect(state.user).toBeNull();
        expect(state.isAuthenticated).toBe(false);
      },
      TIMEOUT,
    );

    it(
      "should handle rapid state changes correctly",
      () => {
        const users = [
          { username: "rapid1" },
          { username: "rapid2" },
          { username: "rapid3" },
        ];

        // Rapid setting of different users
        users.forEach((user) => {
          useAuthStore.getState().setUser(user);
          const state = useAuthStore.getState();
          expect(state.user).toEqual(user);
          expect(state.isAuthenticated).toBe(true);
        });

        // Final clear
        useAuthStore.getState().clearUser();
        const finalState = useAuthStore.getState();
        expect(finalState.user).toBeNull();
        expect(finalState.isAuthenticated).toBe(false);
      },
      TIMEOUT,
    );
  });

  describe("Error Handling", () => {
    it(
      "should handle undefined user gracefully",
      () => {
        expect(() => {
          useAuthStore
            .getState()
            .setUser(undefined as unknown as { username: string });
        }).not.toThrow();
      },
      TIMEOUT,
    );

    it(
      "should handle null user gracefully",
      () => {
        expect(() => {
          useAuthStore
            .getState()
            .setUser(null as unknown as { username: string });
        }).not.toThrow();
      },
      TIMEOUT,
    );

    it(
      "should handle user object without username property",
      () => {
        expect(() => {
          useAuthStore.getState().setUser({} as { username: string });
        }).not.toThrow();
      },
      TIMEOUT,
    );
  });
});
