import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeadCell,
  TableRow,
  Button,
} from "flowbite-react";
import { useEffect, useState, useRef, useCallback } from "react";
import { HiLockClosed, HiOutlineXCircle } from "react-icons/hi2";
import { MdInstallDesktop } from "react-icons/md";
import { useNavigate, useParams } from "react-router-dom";

import { apiClient, isApiError } from "../apiClient";
import InstallModuleModal from "../components/InstallModuleModal";
import MainSkeleton from "../components/MainSkeleton";
import type { ClientInfo } from "../schemas/client";
import type { BasicTaskResponse } from "../schemas/general";
import type { InstalledModuleInfo } from "../schemas/module.ts";
import { useErrorStore } from "../stores/errorStore.ts";

export default function ClientPage() {
  const { username } = useParams<{ username: string }>();
  const navigate = useNavigate();
  const socketRef = useRef<WebSocket | null>(null);
  const { addError, anyErrors } = useErrorStore();

  const [clientInfo, setClientInfo] = useState<ClientInfo | null>(null);
  const [installedModules, setInstalledModules] = useState<
    InstalledModuleInfo[]
  >([]);
  const [showInstallModal, setShowInstallModal] = useState(false);

  const onDelete = async () => {
    const response = await apiClient.delete<BasicTaskResponse>(
      "/client/" + username,
    );
    if (isApiError(response)) {
      addError(`Failed to delete client: ${response.detail}`);
      return;
    }
    navigate("/");
  };

  const onRevokeTokens = async () => {
    const response = await apiClient.delete<BasicTaskResponse>(
      "/client/" + username + "/revoke-tokens",
    );
    if (isApiError(response)) {
      addError(`Failed to revoke tokens: ${response.detail}`);
      return;
    }
  };

  const updateClientAliveStatus = useCallback(
    (clientUsername: string, alive: boolean) => {
      if (clientUsername === username) {
        setClientInfo((prevClientInfo) =>
          prevClientInfo
            ? {
                ...prevClientInfo,
                alive,
                last_contact: new Date().toISOString(),
              }
            : null,
        );
      }
    },
    [username],
  );

  const onMessage = useCallback(
    (event: MessageEvent) => {
      try {
        const data = JSON.parse(event.data);
        if (data.type === "alive_update") {
          updateClientAliveStatus(data.data.username, data.data.alive);
        }
      } catch (error) {
        addError("Error parsing WebSocket message: " + error);
      }
    },
    [updateClientAliveStatus, addError],
  );

  useEffect(() => {
    if (!username) return;
    const fetchClientInfo = async () => {
      const response = await apiClient.get<ClientInfo>("/client/" + username);

      if (isApiError(response)) {
        if (response.statusCode === 404) {
          navigate("/404");
        } else if (response.statusCode === 401) {
          navigate("/login");
        }

        addError(
          `Failed to fetch client info (${response.statusCode}): ${response.detail}`,
        );
        return;
      }
      setClientInfo(response);
    };

    fetchClientInfo();
  }, [username, navigate, addError]);

  useEffect(() => {
    if (!username) return;
    const fetchInstalledModules = async () => {
      const response = await apiClient.get<{
        all_installed: InstalledModuleInfo[];
      }>("/module/installed/" + username);
      if (isApiError(response)) {
        if (response.statusCode === 401) {
          navigate("/login");
        }

        addError(
          `Failed to fetch installed modules (${response.statusCode}): ${response.detail}`,
        );
        return;
      }

      setInstalledModules(response.all_installed || []);
    };

    fetchInstalledModules();
  }, [navigate, username, addError]);

  useEffect(() => {
    apiClient.startWebSocket(socketRef, onMessage);

    return () => {
      apiClient.removeWebSocketListener(onMessage);
    };
  }, [onMessage]);

  const handleInstallModule = async (moduleName: string) => {
    if (!username) return;
    const response = await apiClient.post<object, { message: string }>(
      "/module/set-installed/" + username + "?module_name=" + moduleName,
      {},
    );
    if (isApiError(response)) {
      addError(`Failed to install module: ${response.detail}`);
      return;
    }

    const refresh = await apiClient.get<{
      all_installed: InstalledModuleInfo[];
    }>("/module/installed/" + username);
    if (!isApiError(refresh)) {
      setInstalledModules(refresh.all_installed || []);
    }
  };

  const handleRunModule = async (moduleName: string) => {
    if (!username) return;
    const response = await apiClient.get<BasicTaskResponse>(
      "/module/run/" + moduleName + "?client_username=" + username,
    );
    if (isApiError(response)) {
      addError(`Failed to run module: ${response.detail}`);
    }
  };

  return (
    <MainSkeleton baseName={"Client " + (username ?? "")}>
      <div>
        {!username && (
          <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4">
            No username provided
          </div>
        )}
        {username && clientInfo && !anyErrors() ? (
          <>
            <div className="flex gap-6 p-6 items-start">
              {/* First column - Windows logo with overlay button */}
              <div className="relative flex-shrink-0">
                <img
                  src="/windows_default_logo.png"
                  alt="Windows Logo"
                  className="object-contain max-w-none"
                  style={{
                    height: "calc(2.5rem + 7 * 1.75rem + 6 * 0.75rem + 3rem)",
                  }}
                />
                <Button
                  pill
                  color="dark"
                  size="sm"
                  className="absolute bottom-5 right-5"
                  onClick={() =>
                    navigate(`/console/${encodeURIComponent(username)}`)
                  }
                  disabled={clientInfo?.alive !== true}
                >
                  Open Console
                </Button>
              </div>

              {/* Second column - Client information (determines the height) */}
              <div className="flex-1 border border-gray-200 dark:border-gray-700 rounded-lg p-6 bg-white dark:bg-gray-800 shadow-sm">
                <h2 className="text-xl font-semibold mb-4 text-gray-900 dark:text-gray-100 text-center">
                  Client Information
                </h2>
                <div className="space-y-3">
                  <div>
                    <span className="font-medium text-gray-600 dark:text-gray-300">
                      Username:
                    </span>
                    <span className="ml-2 text-gray-900 dark:text-gray-100">
                      {clientInfo.username}
                    </span>
                  </div>
                  <div>
                    <span className="font-medium text-gray-600 dark:text-gray-300">
                      UUID:
                    </span>
                    <span className="ml-2 text-gray-900 dark:text-gray-100 font-mono text-sm">
                      {clientInfo.uuid}
                    </span>
                  </div>
                  <div>
                    <span className="font-medium text-gray-600 dark:text-gray-300">
                      IP Address:
                    </span>
                    <span className="ml-2 text-gray-900 dark:text-gray-100">
                      {clientInfo.ip_address}
                    </span>
                  </div>
                  <div>
                    <span className="font-medium text-gray-600 dark:text-gray-300">
                      Hostname:
                    </span>
                    <span className="ml-2 text-gray-900 dark:text-gray-100">
                      {clientInfo.hostname}
                    </span>
                  </div>
                  <div>
                    <span className="font-medium text-gray-600 dark:text-gray-300">
                      Status:
                    </span>
                    <span
                      className={`ml-2 px-2 py-1 rounded-full text-xs font-medium ${
                        clientInfo.alive
                          ? "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200"
                          : "bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200"
                      }`}
                    >
                      {clientInfo.alive ? "Online" : "Offline"}
                    </span>
                  </div>
                  <div>
                    <span className="font-medium text-gray-600 dark:text-gray-300">
                      Last Contact:
                    </span>
                    <span className="ml-2 text-gray-900 dark:text-gray-100">
                      {new Date(clientInfo.last_contact).toLocaleString()}
                    </span>
                  </div>
                  <div>
                    <span className="font-medium text-gray-600 dark:text-gray-300">
                      Location:
                    </span>
                    <span className="ml-2 text-gray-900 dark:text-gray-100">
                      {clientInfo.last_known_location}
                    </span>
                  </div>
                </div>
              </div>
            </div>

            <div className="p-6">
              <div className="flex items-center justify-between mb-6 gap-3">
                <div className="flex gap-3">
                  <Button
                    pill
                    color="indigo"
                    className="px-6 gap-1"
                    onClick={() => setShowInstallModal(true)}
                    disabled={clientInfo?.alive !== true}
                  >
                    <MdInstallDesktop className="h-5 w-5" />
                    Install
                  </Button>
                </div>
                <h2 className="text-2xl font-semibold text-gray-900 dark:text-gray-100 flex-1 text-center">
                  Installed Modules
                </h2>
                <div className="w-24"></div>
              </div>

              <div className="overflow-x-auto">
                <Table striped>
                  <TableHead>
                    <TableRow>
                      <TableHeadCell>Module Name</TableHeadCell>
                      <TableHeadCell>Version</TableHeadCell>
                      <TableHeadCell>Description</TableHeadCell>
                      <TableHeadCell>Status</TableHeadCell>
                      <TableHeadCell>
                        <span className="sr-only">Actions</span>
                      </TableHeadCell>
                    </TableRow>
                  </TableHead>
                  <TableBody className="divide-y">
                    {installedModules && installedModules.length > 0 ? (
                      installedModules.map((module, index) => (
                        <TableRow key={index}>
                          <TableCell className="whitespace-nowrap font-medium text-gray-900 dark:text-white">
                            {module.name}
                          </TableCell>
                          <TableCell>{module.version}</TableCell>
                          <TableCell>
                            {module.description || "No description available"}
                          </TableCell>
                          <TableCell>{module.status}</TableCell>
                          <TableCell>
                            <button
                              className="font-medium text-cyan-600 hover:underline dark:text-cyan-500 disabled:opacity-50 disabled:no-underline"
                              disabled={clientInfo?.alive !== true}
                              onClick={() => handleRunModule(module.name)}
                            >
                              Run
                            </button>
                          </TableCell>
                        </TableRow>
                      ))
                    ) : (
                      <TableRow>
                        <TableCell
                          colSpan={5}
                          className="text-center text-gray-500 dark:text-gray-400"
                        >
                          No modules installed
                        </TableCell>
                      </TableRow>
                    )}
                  </TableBody>
                </Table>
              </div>
            </div>
          </>
        ) : !anyErrors() ? (
          <p>Loading...</p>
        ) : null}

        <InstallModuleModal
          show={showInstallModal}
          onClose={() => setShowInstallModal(false)}
          onInstall={handleInstallModule}
        />

        <div className="flex justify-end mr-6 gap-3">
          <Button
            pill
            color="indigo"
            className="gap-1"
            onClick={onRevokeTokens}
          >
            <HiLockClosed className="h-5 w-5" />
            Revoke Client Tokens
          </Button>
          <Button pill color="indigo" className="gap-1" onClick={onDelete}>
            <HiOutlineXCircle className="h-5 w-5" />
            Delete Client
          </Button>
        </div>
      </div>
    </MainSkeleton>
  );
}
