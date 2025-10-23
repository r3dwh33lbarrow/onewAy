import { create } from "zustand";

interface RedirectReasonStore {
  reason: string | null;
  setReason: (reason: string) => void;
  clearReason: () => void;
}

export const useRedirectReasonStore = create<RedirectReasonStore>((set) => ({
  reason: null,
  setReason: (reason: string) => set({ reason }),
  clearReason: () => set({ reason: null }),
}));
