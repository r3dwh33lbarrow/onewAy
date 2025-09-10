import MainSkeleton from "../components/MainSkeleton.tsx";
import {useEffect, useState} from "react";
import {apiClient, isApiError} from "../apiClient.ts";
import type {ClientInfo} from "../schemas/client.ts";
import {useNavigate} from "react-router-dom";

interface ClientPageProps {
  username: string;
}

export default function ClientPage({ username }: ClientPageProps) {
  const navigate = useNavigate();

  const [clientInfo, setClientInfo] = useState<ClientInfo | null>(null);

  useEffect(() => {
    const fetchClientInfo = async() => {
      const response = await apiClient.get<ClientInfo>("/client/get/" + username);

      if (isApiError(response)) {
        if (response.statusCode === 404) {
          navigate("/404")
        }

        return;
      }
      setClientInfo(response);
    };

    fetchClientInfo();
  }, [username, navigate]);

  return (
    <MainSkeleton baseName={"Client " + username}>
      <div>
        {clientInfo ? (
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
              <h2 className="text-xl font-semibold mb-4 text-gray-900 dark:text-gray-100">Client Information</h2>
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
        ) : (
          <p>Loading...</p>
        )}
      </div>
    </MainSkeleton>
  );
}