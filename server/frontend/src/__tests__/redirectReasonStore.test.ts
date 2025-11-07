import { useRedirectReasonStore } from "../stores/redirectReasonStore";

describe("RedirectReasonStore Tests", () => {
  beforeEach(() => {
    useRedirectReasonStore.setState({ reason: null });
  });

  describe("Initial State", () => {
    it("should have null reason initially", () => {
      const state = useRedirectReasonStore.getState();
      expect(state.reason).toBeNull();
    });
  });

  describe("setReason", () => {
    it("should set a reason", () => {
      useRedirectReasonStore.getState().setReason("Session expired");

      const state = useRedirectReasonStore.getState();
      expect(state.reason).toBe("Session expired");
    });

    it("should update existing reason", () => {
      useRedirectReasonStore.getState().setReason("First reason");
      useRedirectReasonStore.getState().setReason("Second reason");

      const state = useRedirectReasonStore.getState();
      expect(state.reason).toBe("Second reason");
    });

    it("should handle empty string reason", () => {
      useRedirectReasonStore.getState().setReason("");

      const state = useRedirectReasonStore.getState();
      expect(state.reason).toBe("");
    });

    it("should handle long reason messages", () => {
      const longReason = "a".repeat(1000);
      useRedirectReasonStore.getState().setReason(longReason);

      const state = useRedirectReasonStore.getState();
      expect(state.reason).toBe(longReason);
    });

    it("should handle special characters in reason", () => {
      const specialReason = "Error: <script>alert('xss')</script> & \"quotes\"";
      useRedirectReasonStore.getState().setReason(specialReason);

      const state = useRedirectReasonStore.getState();
      expect(state.reason).toBe(specialReason);
    });

    it("should handle multiple rapid updates", () => {
      useRedirectReasonStore.getState().setReason("Reason 1");
      useRedirectReasonStore.getState().setReason("Reason 2");
      useRedirectReasonStore.getState().setReason("Reason 3");
      useRedirectReasonStore.getState().setReason("Final Reason");

      const state = useRedirectReasonStore.getState();
      expect(state.reason).toBe("Final Reason");
    });

    it("should handle unicode and emoji in reasons", () => {
      const unicodeReason = "Session expired 🔒 需要重新登录";
      useRedirectReasonStore.getState().setReason(unicodeReason);

      const state = useRedirectReasonStore.getState();
      expect(state.reason).toBe(unicodeReason);
    });
  });

  describe("clearReason", () => {
    it("should clear the reason", () => {
      useRedirectReasonStore.getState().setReason("Test reason");

      let state = useRedirectReasonStore.getState();
      expect(state.reason).toBe("Test reason");

      useRedirectReasonStore.getState().clearReason();

      state = useRedirectReasonStore.getState();
      expect(state.reason).toBeNull();
    });

    it("should work when no reason is set", () => {
      expect(() => {
        useRedirectReasonStore.getState().clearReason();
      }).not.toThrow();

      const state = useRedirectReasonStore.getState();
      expect(state.reason).toBeNull();
    });

    it("should handle multiple consecutive clears", () => {
      useRedirectReasonStore.getState().setReason("Test");
      useRedirectReasonStore.getState().clearReason();
      useRedirectReasonStore.getState().clearReason();
      useRedirectReasonStore.getState().clearReason();

      const state = useRedirectReasonStore.getState();
      expect(state.reason).toBeNull();
    });
  });

  describe("Complete Workflows", () => {
    it("should handle set-clear-set cycle", () => {
      useRedirectReasonStore.getState().setReason("First reason");

      let state = useRedirectReasonStore.getState();
      expect(state.reason).toBe("First reason");

      useRedirectReasonStore.getState().clearReason();

      state = useRedirectReasonStore.getState();
      expect(state.reason).toBeNull();

      useRedirectReasonStore.getState().setReason("Second reason");

      state = useRedirectReasonStore.getState();
      expect(state.reason).toBe("Second reason");
    });

    it("should handle typical redirect scenario", () => {
      // User gets redirected
      useRedirectReasonStore
        .getState()
        .setReason("Your session has expired. Please log in again.");

      let state = useRedirectReasonStore.getState();
      expect(state.reason).not.toBeNull();
      expect(state.reason).toContain("session has expired");

      // User sees the reason
      const reason = state.reason;
      expect(reason).toBeTruthy();

      // Reason is cleared after being shown
      useRedirectReasonStore.getState().clearReason();

      state = useRedirectReasonStore.getState();
      expect(state.reason).toBeNull();
    });

    it("should handle multiple redirects with different reasons", () => {
      // First redirect
      useRedirectReasonStore.getState().setReason("Authentication required");
      expect(useRedirectReasonStore.getState().reason).toBe(
        "Authentication required",
      );

      useRedirectReasonStore.getState().clearReason();

      // Second redirect
      useRedirectReasonStore.getState().setReason("Access denied");
      expect(useRedirectReasonStore.getState().reason).toBe("Access denied");

      useRedirectReasonStore.getState().clearReason();

      // Third redirect
      useRedirectReasonStore.getState().setReason("Session timeout");
      expect(useRedirectReasonStore.getState().reason).toBe("Session timeout");
    });
  });

  describe("Edge Cases", () => {
    it("should handle whitespace-only reasons", () => {
      useRedirectReasonStore.getState().setReason("   ");

      const state = useRedirectReasonStore.getState();
      expect(state.reason).toBe("   ");
    });

    it("should handle reasons with newlines", () => {
      const multilineReason =
        "Error:\nYour session has expired\nPlease log in again";
      useRedirectReasonStore.getState().setReason(multilineReason);

      const state = useRedirectReasonStore.getState();
      expect(state.reason).toBe(multilineReason);
    });

    it("should handle HTML in reasons", () => {
      const htmlReason = "<div>Session expired</div>";
      useRedirectReasonStore.getState().setReason(htmlReason);

      const state = useRedirectReasonStore.getState();
      expect(state.reason).toBe(htmlReason);
    });
  });
});
