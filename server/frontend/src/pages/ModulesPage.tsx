import {
  Alert,
  Button,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeadCell,
  TableRow,
} from "flowbite-react";
import { useEffect, useState } from "react";
import { HiInformationCircle, HiOutlineUpload } from "react-icons/hi";
import { HiMiniPlus } from "react-icons/hi2";
import { useNavigate } from "react-router-dom";

import MainSkeleton from "../components/MainSkeleton";
import ModuleAddModal from "../components/ModuleAddModal";
import { getAllModules, uploadModuleFolder } from "../services/modules";
import { snakeCaseToTitle } from "../utils";
import type {UserModuleAllResponse} from "../schemas/module.ts";

export default function ModulesPage() {
  const [modules, setModules] = useState<UserModuleAllResponse["modules"]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [alertMsg, setAlertMsg] = useState<string | null>(null);
  const [showAddModal, setShowAddModal] = useState(false);
  const navigate = useNavigate();

  useEffect(() => {
    const fetchModules = async () => {
      try {
        setLoading(true);
        setError(null);
        const result = await getAllModules();

        if ("modules" in result) {
          setModules(result.modules);
        } else {
          setError(result.message || "Failed to fetch modules: Unknown error");
        }
      } catch (err) {
        setError("Failed to fetch modules: " + err);
      } finally {
        setLoading(false);
      }
    };

    fetchModules();
  }, []);

  const uploadAndAdd = () => {
    const fileInput = document.createElement("input");
    fileInput.type = "file";
    fileInput.webkitdirectory = true;
    fileInput.multiple = true;
    fileInput.style.display = "none";

    fileInput.onchange = async (event) => {
      const target = event.target as HTMLInputElement;
      const files = target.files;

      if (!files || files.length === 0) {
        return;
      }

      try {
        setLoading(true);
        setError(null);
        setAlertMsg(null);

        const filesArray = Array.from(files);
        const result = await uploadModuleFolder(filesArray);

        if ("result" in result) {
          setAlertMsg("Module uploaded successfully!");
          const modulesResult = await getAllModules();
          if ("modules" in modulesResult) {
            setModules(modulesResult.modules);
          }
        } else {
          setError(`Upload failed: ${result.message || "Unknown error"}`);
        }
      } catch (error) {
        setError(`Upload failed: ${error}`);
      } finally {
        setLoading(false);
      }

      document.body.removeChild(fileInput);
    };

    document.body.appendChild(fileInput);
    fileInput.click();
  };

  const refreshModules = async () => {
    try {
      setLoading(true);
      setError(null);
      const result = await getAllModules();

      if ("modules" in result) {
        setModules(result.modules);
      } else {
        setError(result.message || "Failed to fetch modules: Unknown error");
      }
    } catch (err) {
      setError("Failed to fetch modules: " + err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <MainSkeleton baseName="Modules">
      <div className="max-w-full">
        <div className="flex gap-4 flex-col">
          {alertMsg && (
            <Alert
              icon={HiInformationCircle}
              color="info"
              className="mb-4 w-full"
              onDismiss={() => setAlertMsg(null)}
            >
              <span>{alertMsg}</span>
            </Alert>
          )}

          {!error && (
            <div className="flex gap-4">
              <Button
                color="indigo"
                pill
                className="px-6 gap-1"
                onClick={uploadAndAdd}
              >
                <HiOutlineUpload className="h-5 w-5" />
                Upload & Add
              </Button>
              <Button
                color="indigo"
                pill
                className="px-6 gap-1"
                onClick={() => setShowAddModal(true)}
              >
                <HiMiniPlus className="h-5 w-5" />
                Add
              </Button>
            </div>
          )}
        </div>

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
            <p className="text-red-800 dark:text-red-200">{error}</p>
          </div>
        )}

        {!loading && !error && (
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
                        {module.binaries_platform.map(
                          (platform, platformIndex) => (
                            <span
                              key={platformIndex}
                              className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200"
                            >
                              {platform}
                            </span>
                          ),
                        )}
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
            <p className="text-gray-500 dark:text-gray-400">
              No modules found.
            </p>
          </div>
        )}
      </div>

      <ModuleAddModal
        show={showAddModal}
        onClose={() => setShowAddModal(false)}
        onModuleAdded={refreshModules}
      />
    </MainSkeleton>
  );
}
