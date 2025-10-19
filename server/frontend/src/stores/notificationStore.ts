import { create } from "zustand";

import { apiClient, type ApiError, isApiError } from "../apiClient.ts";
import type {
  AllBucketsResponse,
  BucketInfo,
} from "../schemas/module_bucket.ts";

interface NotificationStore {
  notifications: BucketInfo[];
  last_updated: Date;
  error: ApiError | null;
  query: () => Promise<void>;
  hasUnread: boolean;
}

export const useNotificationStore = create<NotificationStore>((set, get) => ({
  notifications: [],
  last_updated: new Date(0),
  error: null,
  hasUnread: false,

  query: async () => {
    const now = new Date();
    const lastUpdated = get().last_updated;

    const timeDiff = now.getTime() - lastUpdated.getTime();
    const oneMinute = 60 * 1000;

    if (timeDiff < oneMinute) {
      return;
    }

    const response = await apiClient.get<AllBucketsResponse>(
      "/module/all-buckets",
    );
    console.log(response);
    if (isApiError(response)) {
      set({
        error: response,
      });
      return;
    }

    const buckets = Array.isArray(response.buckets) ? response.buckets : [];
    const hasUnread = buckets.some((bucket) => !bucket.consumed);

    set({
      notifications: buckets,
      last_updated: now,
      hasUnread,
      error: null,
    });
  },
}));
