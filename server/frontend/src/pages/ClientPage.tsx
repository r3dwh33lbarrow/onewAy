import MainSkeleton from "../components/MainSkeleton.tsx";
import {useEffect, useState, useRef} from "react";
import {apiClient, isApiError} from "../apiClient.ts";
import type {ClientInfo} from "../schemas/client.ts";
import type {TokenResponse} from "../schemas/authentication.ts";
import {useNavigate} from "react-router-dom";
import { Table, TableBody, TableCell, TableHead, TableHeadCell, TableRow } from "flowbite-react";

interface ClientPageProps {
  username: string;
}

interface InstalledModuleInfo {
  name: string;
  description?: string;
  version: string;
  status: string;
}

export default function ClientPage({ username }: ClientPageProps) {
  const navigate = useNavigate();
  const socketRef = useRef<WebSocket | null>(null);

  const [clientInfo, setClientInfo] = useState<ClientInfo | null>(null);
  const [installedModules, setInstalledModules] = useState<InstalledModuleInfo[]>([]);
  const [error, setError] = useState<string | null>(null);

  const updateClientAliveStatus = (clientUsername: string, alive: boolean) => {
    if (clientUsername === username) {
      setClientInfo(prevClientInfo =>
        prevClientInfo ? {
          ...prevClientInfo,
          alive,
          last_contact: new Date().toISOString()
        } : null
      );
    }
  };

  useEffect(() => {
    const fetchClientInfo = async() => {
      setError(null);
      const response = await apiClient.get<ClientInfo>("/client/get/" + username);

      if (isApiError(response)) {
        if (response.statusCode === 404) {
          navigate("/404")
        } else if (response.statusCode === 401) {
          navigate("/login");
        }

        setError(`Failed to fetch client info (${response.statusCode}): ${response.detail}`);
        return;
      }
      setClientInfo(response);
    };

    fetchClientInfo();
  }, [username, navigate]);

  useEffect(() => {
    const fetchInstalledModules = async () => {
      setError(null);
      const response = await apiClient.get<InstalledModuleInfo[]>("/user/modules/installed/" + username);
      if (isApiError(response)) {
        if (response.statusCode === 401) {
          navigate("/login");
        }

        setError(`Failed to fetch installed modules (${response.statusCode}): ${response.detail}`);
        return;
      }

      console.log("API Response:", response);
      // Since response is directly an array, not an object with modules property
      setInstalledModules(response || []);
    }

    fetchInstalledModules();
  }, [navigate, username]);

  useEffect(() => {
    const initializeWebSocket = async () => {
      try {
        const tokenResponse = await apiClient.post<object, TokenResponse>("/ws-token", {});
        if ("statusCode" in tokenResponse) {
          console.error("Failed to get WebSocket token:", tokenResponse.message);
          return;
        }

        const wsToken = tokenResponse.access_token;
        const socket = new WebSocket(`ws://localhost:8000/ws?token=${wsToken}`);
        socketRef.current = socket;

        socket.onopen = () => {
          console.log("WebSocket connected");
        };

        socket.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data);
            if (data.type === "alive_update") {
              updateClientAliveStatus(data.data.username, data.data.alive);
            }
          } catch (error) {
            console.error("Error parsing WebSocket message:", error);
          }
        };

        socket.onerror = (error) => {
          console.error("WebSocket error:", error);
        };

        socket.onclose = (event) => {
          console.log("WebSocket connection closed:", event.code, event.reason);
        };

      } catch (error) {
        console.error("Failed to initialize WebSocket:", error);
      }
    };

    initializeWebSocket();

    return () => {
      if (socketRef.current) {
        socketRef.current.close();
      }
    };
  }, []);

  return (
    <MainSkeleton baseName={"Client " + username}>
      <div>
        {error && (
          <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4">
            {error}
          </div>
        )}
        {clientInfo && !error ? (
          <>
            <div className="grid grid-cols-3 gap-6 p-6">
              {/* First column - Windows logo (full height) */}
              <div className="flex justify-center items-center h-full min-h-96 p-4">
                <img
                  src="/windows_default_logo.png"
                  alt="Windows Logo"
                  className="w-full h-full object-contain"
                />
              </div>

              {/* Second and third columns - Client information */}
              <div className="col-span-2 border border-gray-200 dark:border-gray-700 rounded-lg p-6 bg-white dark:bg-gray-800 shadow-sm">
                <h2 className="text-xl font-semibold mb-4 text-gray-900 dark:text-gray-100 text-center">Client Information</h2>
                <div className="space-y-3">
                  <div>
                    <span className="font-medium text-gray-600 dark:text-gray-300">Username:</span>
                    <span className="ml-2 text-gray-900 dark:text-gray-100">{clientInfo.username}</span>
                  </div>
                  <div>
                    <span className="font-medium text-gray-600 dark:text-gray-300">UUID:</span>
                    <span className="ml-2 text-gray-900 dark:text-gray-100 font-mono text-sm">{clientInfo.uuid}</span>
                  </div>
                  <div>
                    <span className="font-medium text-gray-600 dark:text-gray-300">IP Address:</span>
                    <span className="ml-2 text-gray-900 dark:text-gray-100">{clientInfo.ip_address}</span>
                  </div>
                  <div>
                    <span className="font-medium text-gray-600 dark:text-gray-300">Hostname:</span>
                    <span className="ml-2 text-gray-900 dark:text-gray-100">{clientInfo.hostname}</span>
                  </div>
                  <div>
                    <span className="font-medium text-gray-600 dark:text-gray-300">Status:</span>
                    <span className={`ml-2 px-2 py-1 rounded-full text-xs font-medium ${
                      clientInfo.alive 
                        ? 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200' 
                        : 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200'
                    }`}>
                      {clientInfo.alive ? 'Online' : 'Offline'}
                    </span>
                  </div>
                  <div>
                    <span className="font-medium text-gray-600 dark:text-gray-300">Last Contact:</span>
                    <span className="ml-2 text-gray-900 dark:text-gray-100">{new Date(clientInfo.last_contact).toLocaleString()}</span>
                  </div>
                  <div>
                    <span className="font-medium text-gray-600 dark:text-gray-300">Location:</span>
                    <span className="ml-2 text-gray-900 dark:text-gray-100">{clientInfo.last_known_location}</span>
                  </div>
                </div>
              </div>
            </div>

            <div className="p-6">
              <h2 className="text-2xl font-semibold mb-6 text-gray-900 dark:text-gray-100 text-center">Installed Modules</h2>

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
                          <TableCell>{module.description || 'No description available'}</TableCell>
                          <TableCell>
                              {module.status}
                          </TableCell>
                          <TableCell>
                            <button className="font-medium text-cyan-600 hover:underline dark:text-cyan-500 disabled:opacity-50 disabled:no-underline"
                            disabled={clientInfo?.alive !== true}>
                              Run
                            </button>
                          </TableCell>
                        </TableRow>
                      ))
                    ) : (
                      <TableRow>
                        <TableCell colSpan={5} className="text-center text-gray-500 dark:text-gray-400">
                          No modules installed
                        </TableCell>
                      </TableRow>
                    )}
                  </TableBody>
                </Table>
              </div>
            </div>
          </>
        ) : (
          <p>Loading...</p>
        )}
      </div>
    </MainSkeleton>
  );
}