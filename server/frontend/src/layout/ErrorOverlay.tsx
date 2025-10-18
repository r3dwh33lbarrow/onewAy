import { useEffect, useState } from "react";

import { useErrorStore } from "../stores/errorStore.ts";

export function ErrorOverlay() {
  const { errors } = useErrorStore();
  const [removingIds, setRemovingIds] = useState<Set<number>>(new Set());
  const [visibleErrors, setVisibleErrors] = useState(errors);

  useEffect(() => {
    const currentIds = new Set(errors.map((e) => e.id));
    const removedErrors = visibleErrors.filter((e) => !currentIds.has(e.id));

    if (removedErrors.length > 0) {
      setRemovingIds(new Set(removedErrors.map((e) => e.id)));
      setTimeout(() => {
        setVisibleErrors(errors);
        setRemovingIds(new Set());
      }, 300);
    } else {
      setVisibleErrors(errors);
    }
  }, [errors, removingIds, visibleErrors]);

  if (visibleErrors.length === 0) return null;

  return (
    <div className="pointer-events-none mb-4">
      {visibleErrors.map((error) => (
        <div
          key={error.id}
          className={`
            bg-red-50 dark:bg-red-900/20 
            border border-red-200 dark:border-red-800 
            rounded-lg p-4 pointer-events-auto
            transition-all duration-300 ease-out
            mb-4
            ${
              removingIds.has(error.id)
                ? "opacity-0 translate-x-full scale-95"
                : "opacity-100 translate-x-0 scale-100"
            }
          `}
        >
          {error.message}
        </div>
      ))}
    </div>
  );
}
