import { Button, Modal, ModalBody, ModalHeader } from "flowbite-react";
import { useEffect, useState } from "react";

import { apiClient, isApiError } from "../apiClient";
import type { UserModuleAllResponse } from "../schemas/module.ts";
import { useErrorStore } from "../stores/errorStore.ts";

interface InstallModuleModalProps {
  show: boolean;
  onClose: () => void;
  onInstall: (moduleName: string) => void;
}

export default function InstallModuleModal({
  show,
  onClose,
  onInstall,
}: InstallModuleModalProps) {
  const [loading, setLoading] = useState(true);
  const [modules, setModules] = useState<string[]>([]);
  const [selectedModule, setSelectedModule] = useState<string | null>(null);

  const { addError, anyErrors } = useErrorStore();

  useEffect(() => {
    const fetchModules = async () => {
      setLoading(true);
      const response =
        await apiClient.get<UserModuleAllResponse>("/module/all");
      if (isApiError(response)) {
        addError(
          `Failed to fetch modules (${response.statusCode}): ${response.detail}`,
        );
        return;
      }

      setModules(response.modules.map((module) => module.name));
      setLoading(false);
    };

    fetchModules();
  }, [addError]);

  return (
    <Modal show={show} onClose={onClose} size="2xl">
      <ModalHeader>Select Module to Install</ModalHeader>
      <ModalBody className="space-y-6">
        {loading && (
          <div className="animate-pulse space-y-2">
            <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-3/4"></div>
            <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-1/2"></div>
            <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-5/6"></div>
          </div>
        )}

        {!loading && !anyErrors() && modules.length > 0 && (
          <>
            <div className="space-y-3">
              <h3 className="text-lg font-medium text-gray-900 dark:text-gray-100">
                Available Modules:
              </h3>
              <div className="max-h-64 overflow-y-auto space-y-2">
                {modules.map((moduleName) => (
                  <div
                    key={moduleName}
                    className={`p-3 border rounded-lg cursor-pointer transition-colors ${
                      selectedModule === moduleName
                        ? "border-blue-500 bg-blue-50 dark:bg-blue-900/20 dark:border-blue-400"
                        : "border-gray-200 dark:border-gray-700 hover:border-gray-300 dark:hover:border-gray-600 hover:bg-gray-50 dark:hover:bg-gray-800"
                    }`}
                    onClick={() => setSelectedModule(moduleName)}
                  >
                    <p className="font-medium text-gray-900 dark:text-gray-100">
                      {moduleName}
                    </p>
                  </div>
                ))}
              </div>
            </div>

            <div className="flex justify-end space-x-3 pt-4 border-t border-gray-200 dark:border-gray-700">
              <Button color="gray" onClick={onClose}>
                Cancel
              </Button>
              <Button
                color="indigo"
                disabled={!selectedModule}
                onClick={() => {
                  if (selectedModule) {
                    onInstall(selectedModule);
                    onClose();
                  }
                }}
              >
                Install
              </Button>
            </div>
          </>
        )}

        {!loading && !anyErrors() && modules.length === 0 && (
          <div className="text-center py-8">
            <p className="text-gray-500 dark:text-gray-400">
              No modules available for installation.
            </p>
          </div>
        )}
      </ModalBody>
    </Modal>
  );
}
