import MainSkeleton from "../components/MainSkeleton.tsx";
import type {UserModuleAllResponse} from "../services/modules.ts";
import { getAllModules } from "../services/modules.ts";
import { Table, TableBody, TableCell, TableHead, TableHeadCell, TableRow } from "flowbite-react";
import { useEffect, useState } from "react";

export default function ModulesPage() {
  const [modules, setModules] = useState<UserModuleAllResponse["modules"]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchModules = async () => {
      try {
        setLoading(true);
        setError(null);
        const result = await getAllModules();

        if ("modules" in result) {
          setModules(result.modules);
        } else {
          // Handle ApiError
          setError(result.message || "Failed to fetch modules");
        }
      } catch (err) {
        setError("An unexpected error occurred");
        console.error("Error fetching modules:", err);
      } finally {
        setLoading(false);
      }
    };

    fetchModules();
  }, []);

  return (
    <MainSkeleton baseName="Modules">
      <div className="space-y-6">
        {loading && (
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
        )}

        {error && (
          <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4">
            <p className="text-red-800 dark:text-red-200">Error: {error}</p>
          </div>
        )}

        {!loading && !error && (
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow">
            <Table>
              <TableHead>
                <TableHeadCell>Module Name</TableHeadCell>
                <TableHeadCell>Version</TableHeadCell>
                <TableHeadCell>Supported Platforms</TableHeadCell>
              </TableHead>
              <TableBody className="divide-y">
                {modules.map((module, index) => (
                  <TableRow key={`${module.name}-${module.version}-${index}`} className="bg-white dark:border-gray-700 dark:bg-gray-800">
                    <TableCell className="whitespace-nowrap font-medium text-gray-900 dark:text-white">
                      {module.name}
                    </TableCell>
                    <TableCell>
                      {module.version}
                    </TableCell>
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
        )}

        {!loading && !error && modules.length === 0 && (
          <div className="text-center py-8">
            <p className="text-gray-500 dark:text-gray-400">No modules found.</p>
          </div>
        )}
      </div>
    </MainSkeleton>
  );
}