import {
  Button,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeadCell,
  TableRow,
} from "flowbite-react";
import { useEffect, useState } from "react";
import { HiOutlineUpload } from "react-icons/hi";
import { HiMiniPlus } from "react-icons/hi2";
import { useNavigate } from "react-router-dom";

import MainSkeleton from "../components/MainSkeleton";
import ModuleAddModal from "../components/ModuleAddModal";
import type { UserModuleAllResponse } from "../services/modules";
import { getAllModules, uploadModuleFolder } from "../services/modules";
import { snakeCaseToTitle } from "../utils";

export default function ModulesPage() {
  const [modules, setModules] = useState<UserModuleAllResponse["modules"]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
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

  const uploadAndAdd = () => {
    const fileInput = document.createElement("input");
    fileInput.type = "file";
    fileInput.webkitdirectory = true; // Enable directory selection
    fileInput.multiple = true; // Required for directory uploads
    fileInput.style.display = "none";

    fileInput.onchange = async (event) => {
      const target = event.target as HTMLInputElement;
      const files = target.files;

      if (!files || files.length === 0) {
        return;
      }

      try {
        setLoading(true);

        // Convert FileList to Array for easier handling
        const filesArray = Array.from(files);

        // You can now process the files with their relative paths
        // files[i].webkitRelativePath contains the path relative to the selected folder
        console.log(
          "Selected files:",
          filesArray.map((f) => f.webkitRelativePath),
        );

        const result = await uploadModuleFolder(filesArray);

        if ("result" in result) {
          alert("Module uploaded successfully!");
          // Refresh the modules list
          const modulesResult = await getAllModules();
          if ("modules" in modulesResult) {
            setModules(modulesResult.modules);
          }
        } else {
          // Handle ApiError
          console.error("Upload API Error:", result);
          alert(`Upload failed: ${result.message || "Unknown error"}`);
        }
      } catch (error) {
        console.error("Upload error:", error);
        alert("Upload failed. Please try again.");
      } finally {
        setLoading(false);
      }

      // Clean up
      document.body.removeChild(fileInput);
    };

    // Trigger folder selection dialog immediately on user click
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
        setError(result.message || "Failed to fetch modules");
      }
    } catch (err) {
      setError("An unexpected error occurred");
      console.error("Error fetching modules:", err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <MainSkeleton baseName="Modules">
      <div className="space-y-6">
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
