import { create } from "zustand";

interface ErrorItem {
  id: number;
  message: string;
}

interface ErrorStore {
  errors: ErrorItem[];
  addError: (message: string) => void;
  removeError: (id: number) => void;
  clearErrors: () => void;
}

export const useErrorStore = create<ErrorStore>((set) => ({
  errors: [],
  addError: (message) =>
    set((state) => ({
      errors: [...state.errors, { id: Date.now(), message }],
    })),
  removeError: (id) =>
    set((state) => ({
      errors: state.errors.filter((e) => e.id !== id),
    })),
  clearErrors: () => set({ errors: [] }),
}));
