import { create } from "zustand";
import { apiClient, isApiError } from "../apiClient.ts";

interface AvatarState {
  avatarUrl: string | null;
  error: string | null;
  fetchAvatar: () => Promise<void>;
  clearAvatar: () => void;
}

export const useAvatarStore = create<AvatarState>((set) => ({
  avatarUrl: null,
  error: null,

  fetchAvatar: async () => {
    try {
      const avatarData = await apiClient.requestBytes("/user/get-avatar", {
        method: "GET",
      });

      if (isApiError(avatarData)) {
        set({
          error: `Failed to fetch avatar (${avatarData.statusCode}): ${avatarData.detail}`,
          avatarUrl: null,
        });
        return;
      }

      const blob = new Blob([avatarData], { type: "image/png" });
      const url = URL.createObjectURL(blob);

      set({ avatarUrl: url, error: null });
    } catch {
      set({ error: "Unexpected error fetching avatar", avatarUrl: null });
    }
  },

  clearAvatar: () => {
    set((state) => {
      if (state.avatarUrl) {
        URL.revokeObjectURL(state.avatarUrl);
      }
      return { avatarUrl: null, error: null };
    });
  },
}));