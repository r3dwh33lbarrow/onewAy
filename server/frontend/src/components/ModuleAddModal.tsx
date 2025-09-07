import {Modal, ModalBody, ModalHeader} from "flowbite-react";
import {useEffect, useState} from "react";
import {apiClient, isApiError} from "../apiClient.ts";
import { HiOutlineDocument, HiOutlineFolder } from "react-icons/hi";


interface ModuleDirectoryContents {
  contents: Array<Record<string, string>>;
}

interface ModuleAddRequest {
  module_path: string;
}

interface ModuleAddModalProps {
  show: boolean;
  onClose: () => void;
}

export default function ModuleAddModal({show, onClose}: ModuleAddModalProps) {
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [directoryContents, setDirectoryContents] = useState<Array<Record<string, string>> | null>(null);
  const [selectedContent, setSelectedContent] = useState<string |null>(null);

  function hasKeyFile<T extends Record<string, string>>(
    record: T
  ): record is T & { file: string } {
    return "file" in record;
  }

  function hasKeyDirectory<T extends Record<string, string>>(
    record: T
  ): record is T & { directory: string } {
    return "directory" in record;
  }

  useEffect(() => {
    if (!show) return;

    const fetchModuleDir = async () => {
      try {
        setLoading(true);
        setError(null);
        const result = await apiClient.get<ModuleDirectoryContents>("/user/modules/query-module-dir");
        
        if (isApiError(result)) {
          setError(result.message);
          return;
        }
        
        setDirectoryContents(result.contents || []);
      } catch {
        setError("Failed to fetch module directory");
      } finally {
        setLoading(false);
      }
    }
    
    fetchModuleDir();
  }, [show]);

  const handleAdd = async () => {
    if (!selectedContent) { return; }
    const response = await apiClient.post<ModuleAddRequest, { message: string }>("/user/modules/add", { module_path: selectedContent });
    if (isApiError(response)) {
      console.error("Error adding module:", response.detail);
    }

    onClose();
  }

  return (
    <Modal show={show} onClose={onClose} size="lg">
      <ModalHeader>Select Module from Directory</ModalHeader>
      <ModalBody className="space-y-6">
        {error && (
          <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-3">
            <p className="text-red-800 dark:text-red-200">{error}</p>
          </div>
        )}

        {loading && (
          <div className="animate-pulse space-y-2">
            <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-3/4"></div>
            <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-1/2"></div>
            <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-5/6"></div>
          </div>
        )}

        {!loading && !error && directoryContents && (
          <>
            {directoryContents.length > 0 ? (
              <div className="space-y-2">
                <p className="text-sm font-medium text-gray-700 dark:text-gray-300">
                  Select a module from the directory:
                </p>
                { /* TODO: Bug with left content space. Feature for now */ }
                <div className="max-h-60 overflow-y-auto border border-gray-200 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 overflow-hidden">
                  {directoryContents.map((item, index) => {
                    const itemValue = hasKeyFile(item) ? item.file : hasKeyDirectory(item) ? item.directory : null;
                    const isSelected = selectedContent === itemValue;
                    const isFirst = index === 0;
                    const isLast = index === directoryContents.length - 1;

                    return (
                      <div
                        key={index}
                        onClick={() => setSelectedContent(itemValue)}
                        className={`cursor-pointer border-b border-gray-200 dark:border-gray-700 last:border-b-0 hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors relative ${
                          isSelected
                            ? `bg-blue-50 dark:bg-blue-900/20 ${
                                isFirst ? 'rounded-t-lg' : ''
                              } ${
                                isLast ? 'rounded-b-lg' : ''
                              }`
                            : `${
                                isFirst ? 'rounded-t-lg' : ''
                              } ${
                                isLast ? 'rounded-b-lg' : ''
                              }`
                        }`}
                      >
                        {isSelected && (
                          <div className="absolute left-0 top-0 bottom-0 w-1 bg-blue-600"></div>
                        )}
                        <div className="p-3 flex items-center gap-3">
                          {hasKeyFile(item) ? <HiOutlineDocument className="w-5 h-5 text-gray-500" /> : hasKeyDirectory(item) ? <HiOutlineFolder className="w-5 h-5 text-gray-500" /> : null}
                          <div className="flex-1 min-w-0">
                            <div className="font-medium text-gray-900 dark:text-white truncate">
                              {itemValue}
                            </div>
                          </div>
                          {isSelected && (
                            <div className="ml-2">
                              <svg className="w-5 h-5 text-blue-600" fill="currentColor" viewBox="0 0 20 20">
                                <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                              </svg>
                            </div>
                          )}
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            ) : (
              <div className="text-center py-8">
                <HiOutlineFolder className="w-12 h-12 text-gray-400 mx-auto mb-3" />
                <p className="text-gray-500 dark:text-gray-400 font-medium">
                  No modules found in directory
                </p>
                <p className="text-sm text-gray-400 dark:text-gray-500 mt-1">
                  Upload modules first using the "Upload & Add" button
                </p>
              </div>
            )}

            <div className="flex justify-end gap-3 pt-4 border-t border-gray-200 dark:border-gray-700">
              <button
                onClick={onClose}
                className="px-4 py-2 rounded-lg font-medium bg-gray-100 hover:bg-gray-200 dark:bg-gray-700 dark:hover:bg-gray-600 text-gray-700 dark:text-gray-300 transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleAdd}
                disabled={!selectedContent}
                className={`px-6 py-2 rounded-lg font-medium transition-colors ${
                  selectedContent
                    ? 'bg-blue-600 hover:bg-blue-700 text-white'
                    : 'bg-gray-300 text-gray-500 cursor-not-allowed dark:bg-gray-600 dark:text-gray-400'
                }`}
              >
                Add
              </button>
            </div>
          </>
        )}
      </ModalBody>
    </Modal>
  );
}