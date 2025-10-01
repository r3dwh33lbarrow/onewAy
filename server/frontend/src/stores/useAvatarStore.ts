import { create } from "zustand";

import { apiClient, isApiError } from "../apiClient";

interface AvatarState {
  avatarUrl: string | null;
  error: string | null;
  fetchAvatar: () => Promise<void>;
  clearAvatar: () => void;
}

function getCachedAvatar(): string | null {
  try {
    return localStorage.getItem("avatarDataUrl");
  } catch {
    return null;
  }
}

function cacheAvatar(dataUrl: string) {
  try {
    localStorage.setItem("avatarDataUrl", dataUrl);
  } catch {
    // Ignore quota or privacy mode errors
  }
}

function clearCachedAvatar() {
  try {
    localStorage.removeItem("avatarDataUrl");
  } catch {
    // ignore
  }
}

export const useAvatarStore = create<AvatarState>((set) => ({
  avatarUrl: getCachedAvatar(),
  error: null,

  fetchAvatar: async () => {
    try {
      const avatarData = await apiClient.requestBytes("/user/avatar", {
        method: "GET",
      });

      if (isApiError(avatarData)) {
        set({
          error: `Failed to fetch avatar (${avatarData.statusCode}): ${avatarData.detail}`,
          avatarUrl: null,
        });
        return;
      }

      // Convert to base64 data URL for stable caching across navigations
      const bytes = new Uint8Array(avatarData as ArrayBuffer);
      let binary = "";
      for (let i = 0; i < bytes.byteLength; i++) {
        binary += String.fromCharCode(bytes[i]);
      }
      const base64 = btoa(binary);
      const dataUrl = `data:image/png;base64,${base64}`;

      cacheAvatar(dataUrl);
      set({ avatarUrl: dataUrl, error: null });
    } catch {
      set({ error: "Unexpected error fetching avatar", avatarUrl: null });
    }
  },

  clearAvatar: () => {
    clearCachedAvatar();
    set({ avatarUrl: null, error: null });
  },
}));
