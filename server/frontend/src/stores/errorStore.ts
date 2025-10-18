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
  anyErrors: () => boolean;
}

export const useErrorStore = create<ErrorStore>((set, get) => ({
  errors: [],
  addError: (message) => {
    const id = Date.now();
    set((state) => ({
      errors: [...state.errors, { id: id, message }],
    }));

    setTimeout(() => {
      set((state) => ({
        errors: state.errors.filter((e) => e.id !== id),
      }));
    }, 5000);
  },
  removeError: (id) =>
    set((state) => ({
      errors: state.errors.filter((e) => e.id !== id),
    })),
  clearErrors: () => set({ errors: [] }),
  anyErrors: () => get().errors.length > 0,
}));
