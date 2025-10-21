import { Alert, Button } from "flowbite-react";
import { useState } from "react";
import { HiInformationCircle, HiOutlineUpload } from "react-icons/hi";
import { HiMiniPlus } from "react-icons/hi2";

import { apiClient } from "../apiClient";
import MainSkeleton from "../components/MainSkeleton";
import ModuleAddModal from "../components/ModuleAddModal";
import ModuleTable from "../components/ModuleTable";
import type { UploadModuleResponse } from "../schemas/module.ts";
import { useErrorStore } from "../stores/errorStore.ts";

export default function ModulesPage() {
  const { addError, anyErrors } = useErrorStore();

  const [alertMsg, setAlertMsg] = useState<string | null>(null);
  const [showAddModal, setShowAddModal] = useState(false);
  const [refreshKey, setRefreshKey] = useState(0);

  const refreshModules = () => {
    setRefreshKey((prev) => prev + 1);
  };

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
        setAlertMsg(null);

        const filesArray = Array.from(files);
        const result = await apiClient.uploadFolder<UploadModuleResponse>(
          "/module/upload",
          filesArray,
          "PUT",
        );

        if ("result" in result) {
          setAlertMsg("Module uploaded successfully!");
          refreshModules();
        } else {
          addError(`Upload failed: ${result.message || "Unknown error"}`);
        }
      } catch (error) {
        addError(`Upload failed: ${error}`);
      }

      document.body.removeChild(fileInput);
    };

    document.body.appendChild(fileInput);
    fileInput.click();
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

          {!anyErrors() && (
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

        {!anyErrors() && <ModuleTable key={refreshKey} />}
      </div>

      <ModuleAddModal
        show={showAddModal}
        onClose={() => setShowAddModal(false)}
        onModuleAdded={refreshModules}
      />
    </MainSkeleton>
  );
}
