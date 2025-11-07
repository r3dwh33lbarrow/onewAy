import { useErrorStore } from "../stores/errorStore";

describe("ErrorStore Tests", () => {
  beforeEach(() => {
    useErrorStore.setState({ errors: [] });
    jest.clearAllMocks();
  });

  afterEach(() => {
    jest.clearAllTimers();
    jest.useRealTimers();
  });

  describe("Initial State", () => {
    it("should have empty errors array initially", () => {
      const state = useErrorStore.getState();
      expect(state.errors).toEqual([]);
      expect(state.anyErrors()).toBe(false);
    });
  });

  describe("addError", () => {
    it("should add an error to the store", () => {
      jest.useFakeTimers();

      useErrorStore.getState().addError("Test error message");
      const state = useErrorStore.getState();

      expect(state.errors).toHaveLength(1);
      expect(state.errors[0].message).toBe("Test error message");
      expect(typeof state.errors[0].id).toBe("number");
      expect(state.anyErrors()).toBe(true);
    });

    it("should add multiple errors", () => {
      jest.useFakeTimers();

      useErrorStore.getState().addError("Error 1");
      jest.advanceTimersByTime(1);
      useErrorStore.getState().addError("Error 2");
      jest.advanceTimersByTime(1);
      useErrorStore.getState().addError("Error 3");

      const state = useErrorStore.getState();
      expect(state.errors).toHaveLength(3);
      expect(state.errors[0].message).toBe("Error 1");
      expect(state.errors[1].message).toBe("Error 2");
      expect(state.errors[2].message).toBe("Error 3");
    });

    it("should assign unique IDs to each error", () => {
      jest.useFakeTimers();

      useErrorStore.getState().addError("Error 1");
      jest.advanceTimersByTime(1);
      useErrorStore.getState().addError("Error 2");

      const state = useErrorStore.getState();
      expect(state.errors[0].id).not.toBe(state.errors[1].id);
    });

    it("should automatically remove error after 5 seconds", () => {
      jest.useFakeTimers();

      useErrorStore.getState().addError("Auto-remove error");

      let state = useErrorStore.getState();
      expect(state.errors).toHaveLength(1);

      jest.advanceTimersByTime(5000);

      state = useErrorStore.getState();
      expect(state.errors).toHaveLength(0);
      expect(state.anyErrors()).toBe(false);
    });

    it("should handle long error messages", () => {
      jest.useFakeTimers();

      const longMessage = "a".repeat(1000);
      useErrorStore.getState().addError(longMessage);

      const state = useErrorStore.getState();
      expect(state.errors[0].message).toBe(longMessage);
      expect(state.errors[0].message.length).toBe(1000);
    });

    it("should handle special characters in error messages", () => {
      jest.useFakeTimers();

      const specialMessage =
        "Error: <script>alert('xss')</script> & \"quotes\"";
      useErrorStore.getState().addError(specialMessage);

      const state = useErrorStore.getState();
      expect(state.errors[0].message).toBe(specialMessage);
    });
  });

  describe("removeError", () => {
    it("should remove a specific error by ID", () => {
      jest.useFakeTimers();

      useErrorStore.getState().addError("Error 1");
      jest.advanceTimersByTime(1);
      useErrorStore.getState().addError("Error 2");
      jest.advanceTimersByTime(1);
      useErrorStore.getState().addError("Error 3");

      const state = useErrorStore.getState();
      const idToRemove = state.errors[1].id;

      useErrorStore.getState().removeError(idToRemove);

      const newState = useErrorStore.getState();
      expect(newState.errors).toHaveLength(2);
      expect(newState.errors.find((e) => e.id === idToRemove)).toBeUndefined();
    });

    it("should not affect other errors when removing one", () => {
      jest.useFakeTimers();

      useErrorStore.getState().addError("Keep this");
      jest.advanceTimersByTime(1);
      useErrorStore.getState().addError("Remove this");

      const state = useErrorStore.getState();
      const removeId = state.errors[1].id;
      const keepId = state.errors[0].id;

      useErrorStore.getState().removeError(removeId);

      const newState = useErrorStore.getState();
      expect(newState.errors).toHaveLength(1);
      expect(newState.errors[0].id).toBe(keepId);
      expect(newState.errors[0].message).toBe("Keep this");
    });

    it("should handle removing non-existent error ID gracefully", () => {
      jest.useFakeTimers();

      useErrorStore.getState().addError("Error 1");

      expect(() => {
        useErrorStore.getState().removeError(999999);
      }).not.toThrow();

      const state = useErrorStore.getState();
      expect(state.errors).toHaveLength(1);
    });

    it("should update anyErrors() when last error is removed", () => {
      jest.useFakeTimers();

      useErrorStore.getState().addError("Only error");

      let state = useErrorStore.getState();
      const errorId = state.errors[0].id;
      expect(state.anyErrors()).toBe(true);

      useErrorStore.getState().removeError(errorId);

      state = useErrorStore.getState();
      expect(state.anyErrors()).toBe(false);
    });
  });

  describe("clearErrors", () => {
    it("should remove all errors", () => {
      jest.useFakeTimers();

      useErrorStore.getState().addError("Error 1");
      useErrorStore.getState().addError("Error 2");
      useErrorStore.getState().addError("Error 3");

      let state = useErrorStore.getState();
      expect(state.errors).toHaveLength(3);

      useErrorStore.getState().clearErrors();

      state = useErrorStore.getState();
      expect(state.errors).toHaveLength(0);
      expect(state.anyErrors()).toBe(false);
    });

    it("should work when called on empty errors", () => {
      expect(() => {
        useErrorStore.getState().clearErrors();
      }).not.toThrow();

      const state = useErrorStore.getState();
      expect(state.errors).toEqual([]);
    });

    it("should clear errors multiple times without issues", () => {
      jest.useFakeTimers();

      useErrorStore.getState().addError("Error");
      useErrorStore.getState().clearErrors();
      useErrorStore.getState().clearErrors();
      useErrorStore.getState().clearErrors();

      const state = useErrorStore.getState();
      expect(state.errors).toHaveLength(0);
    });
  });

  describe("anyErrors", () => {
    it("should return false when no errors exist", () => {
      const state = useErrorStore.getState();
      expect(state.anyErrors()).toBe(false);
    });

    it("should return true when errors exist", () => {
      jest.useFakeTimers();

      useErrorStore.getState().addError("Test error");
      const state = useErrorStore.getState();
      expect(state.anyErrors()).toBe(true);
    });

    it("should update after clearing errors", () => {
      jest.useFakeTimers();

      useErrorStore.getState().addError("Error 1");
      useErrorStore.getState().addError("Error 2");

      let state = useErrorStore.getState();
      expect(state.anyErrors()).toBe(true);

      useErrorStore.getState().clearErrors();

      state = useErrorStore.getState();
      expect(state.anyErrors()).toBe(false);
    });
  });

  describe("Auto-removal timing", () => {
    it("should only remove the specific error after 5 seconds", () => {
      jest.useFakeTimers();

      useErrorStore.getState().addError("Error 1");
      jest.advanceTimersByTime(2000);
      useErrorStore.getState().addError("Error 2");

      jest.advanceTimersByTime(3000);

      let state = useErrorStore.getState();
      expect(state.errors).toHaveLength(1);
      expect(state.errors[0].message).toBe("Error 2");

      jest.advanceTimersByTime(2000);

      state = useErrorStore.getState();
      expect(state.errors).toHaveLength(0);
    });

    it("should handle manual removal before auto-removal", () => {
      jest.useFakeTimers();

      useErrorStore.getState().addError("Will be manually removed");

      const state = useErrorStore.getState();
      const errorId = state.errors[0].id;

      useErrorStore.getState().removeError(errorId);

      jest.advanceTimersByTime(5000);

      const finalState = useErrorStore.getState();
      expect(finalState.errors).toHaveLength(0);
    });
  });

  describe("Edge Cases", () => {
    it("should handle empty string error message", () => {
      jest.useFakeTimers();

      useErrorStore.getState().addError("");

      const state = useErrorStore.getState();
      expect(state.errors).toHaveLength(1);
      expect(state.errors[0].message).toBe("");
    });

    it("should handle rapid successive error additions", () => {
      jest.useFakeTimers();

      for (let i = 0; i < 100; i++) {
        useErrorStore.getState().addError(`Error ${i}`);
      }

      const state = useErrorStore.getState();
      expect(state.errors).toHaveLength(100);
    });

    it("should handle clearing errors while new ones are being added", () => {
      jest.useFakeTimers();

      useErrorStore.getState().addError("Error 1");
      useErrorStore.getState().clearErrors();
      useErrorStore.getState().addError("Error 2");

      const state = useErrorStore.getState();
      expect(state.errors).toHaveLength(1);
      expect(state.errors[0].message).toBe("Error 2");
    });
  });
});
