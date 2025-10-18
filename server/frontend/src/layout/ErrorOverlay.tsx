import { useErrorStore } from "../stores/errorStore.ts";

export function ErrorOverlay() {
  const { errors, removeError } = useErrorStore();
  if (errors.length === 0) return null;

  return (
    <div className="fixed inset-0 z-50 pointer-events-none">
      {errors.map((error) => (
        <div key={error.id} className="pointer-events-auto">
          {error.message}
          <button onClick={() => removeError(error.id)}>×</button>
        </div>
      ))}
    </div>
  );
}