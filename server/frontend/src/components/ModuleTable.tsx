import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeadCell,
  TableRow,
} from "flowbite-react";
import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

import { apiClient } from "../apiClient";
import type { UserModuleAllResponse } from "../schemas/module.ts";
import { useErrorStore } from "../stores/errorStore.ts";
import { snakeCaseToTitle } from "../utils";

interface ModuleTableProps {
  showEmptyState?: boolean;
  onLoadingChange?: (loading: boolean) => void;
}

export default function ModuleTable({
  showEmptyState = true,
  onLoadingChange,
}: ModuleTableProps) {
  const navigate = useNavigate();
  const { addError } = useErrorStore();

  const [modules, setModules] = useState<UserModuleAllResponse["modules"]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchModules = async () => {
      try {
        setLoading(true);
        onLoadingChange?.(true);
        const result =
          await apiClient.get<UserModuleAllResponse>("/module/all");

        if ("modules" in result) {
          setModules(result.modules);
        } else {
          addError(result.message || "Failed to fetch modules: Unknown error");
        }
      } catch (err) {
        addError("Failed to fetch modules: " + err);
      } finally {
        setLoading(false);
        onLoadingChange?.(false);
      }
    };

    fetchModules();
  }, [addError, onLoadingChange]);

  if (loading) {
    return (
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
        <div className="animate-pulse space-y-4">
          <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-1/4"></div>
          <div className="space-y-2">
            <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded"></div>
            <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-5/6"></div>
            <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-4/6"></div>
          </div>
        </div>
      </div>
    );
  }

  if (modules.length === 0 && showEmptyState) {
    return (
      <div className="text-center py-8">
        <p className="text-gray-500 dark:text-gray-400">No modules found.</p>
      </div>
    );
  }

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow mt-6">
      <Table>
        <TableHead>
          <TableRow>
            <TableHeadCell>Module Name</TableHeadCell>
            <TableHeadCell>Description</TableHeadCell>
            <TableHeadCell>Version</TableHeadCell>
            <TableHeadCell>Start</TableHeadCell>
            <TableHeadCell>Supported Platforms</TableHeadCell>
          </TableRow>
        </TableHead>
        <TableBody className="divide-y">
          {modules.map((module, index) => (
            <TableRow
              key={`${module.name}-${module.version}-${index}`}
              className="bg-white dark:border-gray-700 dark:bg-gray-800 hover:bg-gray-50 dark:hover:bg-gray-700 cursor-pointer transition-colors"
              onClick={() => navigate(`/modules/${module.name}`)}
            >
              <TableCell className="whitespace-nowrap font-medium text-gray-900 dark:text-white">
                {snakeCaseToTitle(module.name)}
              </TableCell>
              <TableCell className="whitespace-nowrap text-gray-900 dark:text-white">
                {module.description}
              </TableCell>
              <TableCell>{module.version}</TableCell>
              <TableCell>{module.start}</TableCell>
              <TableCell>
                <div className="flex flex-wrap gap-1">
                  {module.binaries_platform.map((platform, platformIndex) => (
                    <span
                      key={platformIndex}
                      className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200"
                    >
                      {platform}
                    </span>
                  ))}
                </div>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}

