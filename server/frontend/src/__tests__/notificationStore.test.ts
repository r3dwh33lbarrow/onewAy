import { useNotificationStore } from "../stores/notificationStore";
import { apiClient } from "../apiClient";

// Mock the apiClient but keep the actual isApiError implementation
jest.mock("../apiClient", () => {
  const actual = jest.requireActual("../apiClient");
  return {
    ...actual,
    apiClient: {
      get: jest.fn(),
    },
  };
});

const mockApiClient = apiClient as jest.Mocked<typeof apiClient>;

describe("NotificationStore Tests", () => {
  beforeEach(() => {
    useNotificationStore.setState({
      notifications: [],
      last_updated: new Date(0),
      error: null,
      hasUnread: false,
    });
    jest.clearAllMocks();
    jest.useFakeTimers();
  });

  afterEach(() => {
    jest.clearAllTimers();
    jest.useRealTimers();
  });

  describe("Initial State", () => {
    it("should have correct initial state", () => {
      const state = useNotificationStore.getState();

      expect(state.notifications).toEqual([]);
      expect(state.last_updated).toEqual(new Date(0));
      expect(state.error).toBeNull();
      expect(state.hasUnread).toBe(false);
    });
  });

  describe("query", () => {
    it("should fetch notifications and update state", async () => {
      const mockBuckets = [
        { name: "bucket1", consumed: false, created_at: "2024-01-01T00:00:00Z", client_username: "client1", entry_uuid: "uuid1" },
        { name: "bucket2", consumed: true, created_at: "2024-01-01T00:00:00Z", client_username: "client2", entry_uuid: "uuid2" },
      ];

      mockApiClient.get.mockResolvedValue({ buckets: mockBuckets });

      await useNotificationStore.getState().query({ force: true });

      const state = useNotificationStore.getState();
      expect(state.notifications).toEqual(mockBuckets);
      expect(state.hasUnread).toBe(true);
      expect(state.error).toBeNull();
      expect(state.last_updated.getTime()).toBeGreaterThan(0);
    });

    it("should set hasUnread to false when all buckets are consumed", async () => {
      const mockBuckets = [
        { name: "bucket1", consumed: true, created_at: "2024-01-01T00:00:00Z", client_username: null, entry_uuid: null },
        { name: "bucket2", consumed: true, created_at: "2024-01-01T00:00:00Z", client_username: null, entry_uuid: null },
      ];

      mockApiClient.get.mockResolvedValue({ buckets: mockBuckets });

      await useNotificationStore.getState().query({ force: true });

      const state = useNotificationStore.getState();
      expect(state.hasUnread).toBe(false);
    });

    it("should set hasUnread to true when any bucket is unconsumed", async () => {
      const mockBuckets = [
        { name: "bucket1", consumed: true, created_at: "2024-01-01T00:00:00Z", client_username: null, entry_uuid: null },
        { name: "bucket2", consumed: false, created_at: "2024-01-01T00:00:00Z", client_username: null, entry_uuid: null },
        { name: "bucket3", consumed: true, created_at: "2024-01-01T00:00:00Z", client_username: null, entry_uuid: null },
      ];

      mockApiClient.get.mockResolvedValue({ buckets: mockBuckets });

      await useNotificationStore.getState().query({ force: true });

      const state = useNotificationStore.getState();
      expect(state.hasUnread).toBe(true);
    });

    it("should handle API errors", async () => {
      const mockError: any = {
        statusCode: 500,
        message: "Internal Server Error",
        detail: "Something went wrong",
      };

      mockApiClient.get.mockResolvedValue(mockError);

      await useNotificationStore.getState().query({ force: true });

      const state = useNotificationStore.getState();
      // Error should be set when API returns an error
      expect(state.error).toBeTruthy();
      expect(state.error?.statusCode).toBe(500);
    });

    it("should handle empty buckets array", async () => {
      mockApiClient.get.mockResolvedValue({ buckets: [] });

      await useNotificationStore.getState().query({ force: true });

      const state = useNotificationStore.getState();
      expect(state.notifications).toEqual([]);
      expect(state.hasUnread).toBe(false);
    });

    it("should handle non-array buckets response", async () => {
      mockApiClient.get.mockResolvedValue({ buckets: null });

      await useNotificationStore.getState().query({ force: true });

      const state = useNotificationStore.getState();
      expect(state.notifications).toEqual([]);
      expect(state.hasUnread).toBe(false);
    });

    it("should not query if less than 1 minute has passed without force option", async () => {
      const now = new Date();
      useNotificationStore.setState({ last_updated: new Date(now.getTime() - 30000) }); // 30 seconds ago

      await useNotificationStore.getState().query();

      expect(mockApiClient.get).not.toHaveBeenCalled();
    });

    it("should query if more than 1 minute has passed", async () => {
      const now = new Date();
      useNotificationStore.setState({ last_updated: new Date(now.getTime() - 61000) }); // 61 seconds ago

      mockApiClient.get.mockResolvedValue({ buckets: [] });

      await useNotificationStore.getState().query();

      expect(mockApiClient.get).toHaveBeenCalledTimes(1);
    });

    it("should query even if less than 1 minute has passed when force is true", async () => {
      const now = new Date();
      useNotificationStore.setState({ last_updated: new Date(now.getTime() - 10000) }); // 10 seconds ago

      mockApiClient.get.mockResolvedValue({ buckets: [] });

      await useNotificationStore.getState().query({ force: true });

      expect(mockApiClient.get).toHaveBeenCalledTimes(1);
    });

    it("should clear error on successful query", async () => {
      useNotificationStore.setState({
        error: {
          statusCode: 500,
          message: "Previous Error",
          detail: "Error detail",
        },
      });

      mockApiClient.get.mockResolvedValue({ buckets: [] });

      await useNotificationStore.getState().query({ force: true });

      const state = useNotificationStore.getState();
      expect(state.error).toBeNull();
    });
  });

  describe("markAsConsumed", () => {
    it("should mark a specific notification as consumed", () => {
      const mockBuckets = [
        { name: "bucket1", consumed: false, created_at: "2024-01-01T00:00:00Z", client_username: null, entry_uuid: null },
        { name: "bucket2", consumed: false, created_at: "2024-01-01T00:00:00Z", client_username: null, entry_uuid: null },
        { name: "bucket3", consumed: false, created_at: "2024-01-01T00:00:00Z", client_username: null, entry_uuid: null },
      ];

      useNotificationStore.setState({ notifications: mockBuckets });

      useNotificationStore.getState().markAsConsumed("bucket2");

      const state = useNotificationStore.getState();
      expect(state.notifications[0].consumed).toBe(false);
      expect(state.notifications[1].consumed).toBe(true);
      expect(state.notifications[2].consumed).toBe(false);
    });

    it("should update hasUnread flag when marking as consumed", () => {
      const mockBuckets = [
        { name: "bucket1", consumed: false, created_at: "2024-01-01T00:00:00Z", client_username: null, entry_uuid: null },
        { name: "bucket2", consumed: true, created_at: "2024-01-01T00:00:00Z", client_username: null, entry_uuid: null },
      ];

      useNotificationStore.setState({ notifications: mockBuckets, hasUnread: true });

      useNotificationStore.getState().markAsConsumed("bucket1");

      const state = useNotificationStore.getState();
      expect(state.hasUnread).toBe(false);
    });

    it("should keep hasUnread true if other unread notifications exist", () => {
      const mockBuckets = [
        { name: "bucket1", consumed: false, created_at: "2024-01-01T00:00:00Z", client_username: null, entry_uuid: null },
        { name: "bucket2", consumed: false, created_at: "2024-01-01T00:00:00Z", client_username: null, entry_uuid: null },
      ];

      useNotificationStore.setState({ notifications: mockBuckets, hasUnread: true });

      useNotificationStore.getState().markAsConsumed("bucket1");

      const state = useNotificationStore.getState();
      expect(state.hasUnread).toBe(true);
    });

    it("should not affect other notifications when marking one as consumed", () => {
      const mockBuckets = [
        { name: "bucket1", consumed: false, created_at: "2024-01-01T00:00:00Z", client_username: "client1", entry_uuid: "uuid1" },
        { name: "bucket2", consumed: false, created_at: "2024-01-01T00:00:00Z", client_username: "client2", entry_uuid: "uuid2" },
      ];

      useNotificationStore.setState({ notifications: mockBuckets });

      useNotificationStore.getState().markAsConsumed("bucket1");

      const state = useNotificationStore.getState();
      expect(state.notifications[0].name).toBe("bucket1");
      expect(state.notifications[1].name).toBe("bucket2");
      expect(state.notifications[1].consumed).toBe(false);
    });

    it("should handle marking non-existent notification gracefully", () => {
      const mockBuckets = [
        { name: "bucket1", consumed: false, created_at: "2024-01-01T00:00:00Z", client_username: null, entry_uuid: null },
      ];

      useNotificationStore.setState({ notifications: mockBuckets });

      expect(() => {
        useNotificationStore.getState().markAsConsumed("nonexistent");
      }).not.toThrow();

      const state = useNotificationStore.getState();
      expect(state.notifications).toHaveLength(1);
      expect(state.notifications[0].consumed).toBe(false);
    });

    it("should handle marking already consumed notification", () => {
      const mockBuckets = [
        { name: "bucket1", consumed: true, created_at: "2024-01-01T00:00:00Z", client_username: null, entry_uuid: null },
      ];

      useNotificationStore.setState({ notifications: mockBuckets, hasUnread: false });

      useNotificationStore.getState().markAsConsumed("bucket1");

      const state = useNotificationStore.getState();
      expect(state.notifications[0].consumed).toBe(true);
      expect(state.hasUnread).toBe(false);
    });
  });

  describe("Integration scenarios", () => {
    it("should handle complete workflow: query, mark consumed, query again", async () => {
      const mockBuckets = [
        { name: "bucket1", consumed: false, created_at: "2024-01-01T00:00:00Z", client_username: null, entry_uuid: null },
      ];

      mockApiClient.get.mockResolvedValue({ buckets: mockBuckets });

      await useNotificationStore.getState().query({ force: true });

      let state = useNotificationStore.getState();
      expect(state.hasUnread).toBe(true);

      useNotificationStore.getState().markAsConsumed("bucket1");

      state = useNotificationStore.getState();
      expect(state.hasUnread).toBe(false);

      mockApiClient.get.mockResolvedValue({ buckets: mockBuckets });

      await useNotificationStore.getState().query({ force: true });

      state = useNotificationStore.getState();
      expect(state.notifications[0].consumed).toBe(false); // Refreshed from API
      expect(state.hasUnread).toBe(true);
    });

    it("should handle rapid consecutive queries with force", async () => {
      mockApiClient.get.mockResolvedValue({ buckets: [] });

      await Promise.all([
        useNotificationStore.getState().query({ force: true }),
        useNotificationStore.getState().query({ force: true }),
        useNotificationStore.getState().query({ force: true }),
      ]);

      expect(mockApiClient.get).toHaveBeenCalledTimes(3);
    });
  });

  describe("Edge Cases", () => {
    it("should handle buckets with missing fields gracefully", async () => {
      const mockBuckets = [
        { name: "bucket1" }, // missing consumed field
        { consumed: false }, // missing name field
      ] as any;

      mockApiClient.get.mockResolvedValue({ buckets: mockBuckets });

      await useNotificationStore.getState().query({ force: true });

      const state = useNotificationStore.getState();
      expect(state.notifications).toEqual(mockBuckets);
    });

    it("should handle marking consumed on empty notifications array", () => {
      useNotificationStore.setState({ notifications: [] });

      expect(() => {
        useNotificationStore.getState().markAsConsumed("anything");
      }).not.toThrow();

      const state = useNotificationStore.getState();
      expect(state.notifications).toEqual([]);
    });
  });
});
