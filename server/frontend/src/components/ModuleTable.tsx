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
  onModuleTick?: (selectedModules: Record<string, boolean>) => void;
  marginTop?: string;
}

export default function ModuleTable({
  showEmptyState = true,
  onModuleTick,
  marginTop = "mt-6",
}: ModuleTableProps) {
  const navigate = useNavigate();
  const { addError } = useErrorStore();

  const [modules, setModules] = useState<UserModuleAllResponse["modules"]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedModules, setSelectedModules] = useState<
    Record<string, boolean>
  >({});

  useEffect(() => {
    const fetchModules = async () => {
      try {
        setLoading(true);
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
      }
    };

    fetchModules();
  }, [addError]);

  const handleCheckboxChange = (moduleName: string, checked: boolean) => {
    const newSelectedModules = {
      ...selectedModules,
      [moduleName]: checked,
    };
    setSelectedModules(newSelectedModules);
    onModuleTick?.(newSelectedModules);
  };

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
    <div className={"bg-white dark:bg-gray-800 rounded-lg shadow " + marginTop}>
      <Table>
        <TableHead>
          <TableRow>
            <TableHeadCell>Module Name</TableHeadCell>
            <TableHeadCell>Description</TableHeadCell>
            <TableHeadCell>Version</TableHeadCell>
            <TableHeadCell>Start</TableHeadCell>
            <TableHeadCell>Supported Platforms</TableHeadCell>
            {onModuleTick && <TableHeadCell>Install</TableHeadCell>}
          </TableRow>
        </TableHead>
        <TableBody className="divide-y">
          {modules.map((module, index) => (
            <TableRow
              key={`${module.name}-${module.version}-${index}`}
              className="bg-white dark:border-gray-700 dark:bg-gray-800 hover:bg-gray-50 dark:hover:bg-gray-700 cursor-pointer transition-colors"
              onClick={(e) => {
                // Don't navigate if clicking on checkbox
                if (
                  !(e.target as HTMLElement).closest('input[type="checkbox"]')
                ) {
                  navigate(`/modules/${module.name}`);
                }
              }}
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
              {onModuleTick && (
                <TableCell onClick={(e) => e.stopPropagation()}>
                  <input
                    type="checkbox"
                    checked={selectedModules[module.name] || false}
                    onChange={(e) =>
                      handleCheckboxChange(module.name, e.target.checked)
                    }
                    className="w-4 h-4 text-blue-600 bg-gray-100 border-gray-300 rounded focus:ring-blue-500 dark:focus:ring-blue-600 dark:ring-offset-gray-800 focus:ring-2 dark:bg-gray-700 dark:border-gray-600 cursor-pointer"
                  />
                </TableCell>
              )}
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}

