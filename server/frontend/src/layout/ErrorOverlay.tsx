import { useErrorStore } from "../stores/errorStore.ts";

export function ErrorOverlay() {
  const { errors } = useErrorStore();
  if (errors.length === 0) return null;

  return (
    <div className="fixed inset-0 z-50 pointer-events-none">
      {errors.map((error) => (
        <div
          key={error.id}
          className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4"
        >
          {error.message}
        </div>
      ))}
    </div>
  );
}
