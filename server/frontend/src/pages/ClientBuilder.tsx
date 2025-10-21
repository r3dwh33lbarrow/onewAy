import { useState } from "react";

import MainSkeleton from "../components/MainSkeleton.tsx";
import ModuleTable from "../components/ModuleTable.tsx";
import { useErrorStore } from "../stores/errorStore.ts";

export default function ClientBuilder() {
  // TODO: Add autofill
  const [ip, setIp] = useState("");
  const [port, setPort] = useState("");
  const [selectedModules, setSelectedModules] = useState<
    Record<string, boolean>
  >({});
  const { anyErrors } = useErrorStore();

  return (
    <MainSkeleton baseName="Client Builder">
      <p className="font-bold dark:text-gray-400 px-2 mb-1">Configuration</p>
      <div className="h-full rounded-2xl shadow-xl bg-white dark:bg-gray-800 p-4">
        <div className="grid grid-cols-[max-content_1fr] items-center gap-x-4 gap-y-2">
          <p className="">IP Address:</p>
          <input
            type="text"
            placeholder="x.x.x.x"
            className="border border-gray-300 rounded-lg px-4 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:text-gray-300 dark:border-gray-600"
            value={ip}
            onChange={(e) => setIp(e.target.value)}
          />

          <p className="">Port:</p>
          <input
            type="text"
            placeholder="0-65535"
            className="border border-gray-300 rounded-lg px-4 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:text-gray-300 dark:border-gray-600"
            value={port}
            onChange={(e) => setPort(e.target.value)}
          />
        </div>
      </div>

      <p className="font-bold dark:text-gray-400 px-2 mb-1 mt-6">
        Available Modules to Add
      </p>
      {!anyErrors() && <ModuleTable onModuleTick={setSelectedModules} />}
    </MainSkeleton>
  );
}
