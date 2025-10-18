import React from "react";

import { ErrorOverlay } from "../layout/ErrorOverlay.tsx";
import MainSidebar from "../layout/MainSidebar";
import TopIcons from "../layout/TopIcons";

interface MainSkeletonProps {
  baseName: string;
  children: React.ReactNode;
}

export default function MainSkeleton({
  baseName,
  children,
}: MainSkeletonProps) {
  return (
    <div className="min-h-screen bg-gray-100 dark:bg-gray-900">
      <aside className="fixed inset-y-0 flex w-64 flex-col border-r border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900">
        <MainSidebar />
      </aside>
      <div className="pl-64">
        <header className="sticky top-0 z-30 flex h-16 items-center justify-between gap-3 border-b border-gray-200 bg-white/80 backdrop-blur-sm dark:border-gray-800 dark:bg-gray-900/80 px-6">
          <div className="flex items-center gap-3">
            <h1 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
              {baseName}
            </h1>
          </div>

          <TopIcons />
        </header>

        <main className="p-6 text-gray-600 dark:text-gray-200">
          <ErrorOverlay />
          {children}
        </main>
      </div>
    </div>
  );
}
