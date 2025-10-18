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
}

export const useNotificationStore = create<NotificationStore>((set, get) => ({
  notifications: [],
  last_updated: new Date(),
  error: null,

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
    if (isApiError(response)) {
      set({
        error: response,
      });
      return;
    }

    set({
      notifications: response.buckets,
      last_updated: now,
    });
  },
}));
