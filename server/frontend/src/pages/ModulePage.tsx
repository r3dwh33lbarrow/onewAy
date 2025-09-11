import { useState, useEffect } from "react";
import { apiClient, isApiError } from "../apiClient";
import MainSkeleton from "../components/MainSkeleton.tsx";
import {snakeCaseToDashCase, snakeCaseToTitle} from "../utils.ts";
import {Button} from "flowbite-react";
import {HiOutlineTrash, HiRefresh} from "react-icons/hi";

interface ModulePageProps {
  name: string;
}

interface ModuleInfo {
  name: string;
  description?: string;
  version: string;
  binaries: Record<string, string>;
}

export default function ModulePage({ name }: ModulePageProps) {
  const [moduleInfo, setModuleInfo] = useState<ModuleInfo | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchModuleInfo = async () => {
      setError(null);
      const response = await apiClient.get<ModuleInfo>("/user/modules/get/" + snakeCaseToDashCase(name));
      if (isApiError(response)) {
        setError(`Failed to fetch module info (${response.statusCode}): ${response.detail}`);
        return
      }

      setModuleInfo(response);
    }

    fetchModuleInfo();
  }, [name]);

  const handleUpdate = async () => {
    setError(null);

    // Dynamically create file input
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
        const formData = new FormData();
        for (let i = 0; i < files.length; i++) {
          formData.append("files", files[i]);
        }

        const response = await fetch(
          `${apiClient.getApiUrl()}/user/modules/update/${snakeCaseToDashCase(name)}`,
          {
            method: "PUT",
            body: formData,
            credentials: "include",
          }
        );

        if (!response.ok) {
          const err = await response.json();
          setError(
            `Failed to update module (${response.status}): ${
              err.detail || response.statusText
            }`
          );
          return;
        }

        console.log("Update result:", await response.json());
        // Refresh module info
        window.location.reload();
      } catch (err) {
        setError(`Error during update: ${(err as Error).message}`);
      }
    };

    // Trigger file selection
    fileInput.click();
  };

  const handleDelete = async () => {
    setError(null);
    try {
      const response = await apiClient.delete<{ result: string }>(
        `/user/modules/delete/${snakeCaseToDashCase(name)}`
      );

      if (isApiError(response)) {
        setError(
          `Failed to delete module (${response.statusCode}): ${
            response.detail || response.message
          }`
        );
        return;
      }

      console.log("Delete result:", response);
      setModuleInfo(null); // Clear view
    } catch (err) {
      setError(`Error during delete: ${(err as Error).message}`);
    }
  };



  return (
    <MainSkeleton baseName="Module View">
      {error && <p>{error}</p>}
      {moduleInfo && (
        <div className="flex flex-col items-center justify-center">
          <h2 className="text-2xl font-bold mb-2 text-gray-800 dark:text-gray-200">{snakeCaseToTitle(moduleInfo.name)}</h2>
          <div className="border-t w-3/4 border-gray-700 text-gray-900 dark:text-gray-200">
            <p className="mt-4 mb-0.5">Description</p>
            <p className="border rounded border-gray-600 p-3 mb-3">{moduleInfo.description}</p>
            <p className="mb-0.5">Version</p>
            <p className="border rounded border-gray-600 p-3 mb-3">{moduleInfo.version}</p>
            <p className="mb-0.5">Binaries</p>
            <div className="flex flex-wrap gap-2 mb-5">
              {Object.entries(moduleInfo.binaries).map(([platform]) => (
                <span
                  key={platform}
                  className="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200"
                >
                  {platform}
                </span>
              ))}
            </div>

            <div className="flex flex-row gap-3">
              <Button color="indigo" className="px-6 gap-1" pill onClick={handleUpdate}>
                <HiRefresh className="h-5 w-5" />
                Update
              </Button>

              <Button color="indigo" className="px-6 gap-1" pill onClick={handleDelete}>
                <HiOutlineTrash className="h-5 w-5" />
                Delete
              </Button>
            </div>


          </div>
        </div>
      )}
    </MainSkeleton>
  );
}