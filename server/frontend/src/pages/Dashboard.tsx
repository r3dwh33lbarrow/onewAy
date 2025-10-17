import { useState, useEffect, useRef, useCallback } from "react";
import { useNavigate } from "react-router-dom";

import { apiClient, isApiError } from "../apiClient";
import ClientCard from "../components/ClientCard";
import MainSkeleton from "../components/MainSkeleton";
import type { ClientAllResponse, BasicClientInfo } from "../schemas/client";
import { apiErrorToString } from "../utils.ts";

export default function Dashboard() {
  const [loading, setLoading] = useState(true);
  const [clients, setClients] = useState<BasicClientInfo[]>([]);
  const [error, setError] = useState<string | null>(null);
  const navigate = useNavigate();
  const socketRef = useRef<WebSocket | null>(null);

  const updateClientAliveStatus = (username: string, alive: boolean) => {
    setClients((prevClients) =>
      prevClients.map((client) =>
        client.username === username
          ? { ...client, alive, last_contact: new Date().toISOString() }
          : client,
      ),
    );
  };

  const onMessage = useCallback((event: MessageEvent) => {
    try {
      const data = JSON.parse(event.data);
      if (data.type === "alive_update") {
        updateClientAliveStatus(data.data.username, data.data.alive);
      }
    } catch (error) {
      setError("Error parsing WebSocket message: " + error);
    }
  }, []);

  useEffect(() => {
    const fetchClients = async () => {
      try {
        const response = await apiClient.get<ClientAllResponse>("/client/all");
        if (isApiError(response)) {
          if (response.statusCode === 401) {
            navigate("/login");
            return;
          }

          setError(
            `Failed to fetch clients (${response.statusCode}): ${response.detail || response.message}`,
          );
        } else {
          setClients(response.clients);
        }

        setLoading(false);
      } catch (error) {
        setError(`Failed to fetch clients: ${error}`);
        setLoading(false);
      }
    };

    fetchClients();
  }, [navigate]);

  useEffect(() => {
    apiClient.startWebSocket(socketRef, onMessage, (error) =>
      setError(apiErrorToString(error)),
    );

    const currentSocket = socketRef.current;

    return () => {
      currentSocket?.removeEventListener("message", onMessage);
    };
  }, [onMessage]);

  return (
    <MainSkeleton baseName="Dashboard">
      {error && (
        <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-3">
          <p className="text-red-800 dark:text-red-200">{error}</p>
        </div>
      )}

      {!error &&
        (loading ? (
          <div className="rounded-2xl border border-dashed border-gray-300 dark:border-gray-700 p-10 text-center text-sm text-gray-600 dark:text-gray-400">
            Loading...
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
            {clients.map((client, index) => (
              <ClientCard
                key={`${client.username}-${client.ip_address}-${index}`}
                username={client.username}
                ip_address={client.ip_address}
                hostname={client.hostname}
                alive={client.alive}
                last_contact={client.last_contact}
              />
            ))}
            {clients.length === 0 && (
              <div className="col-span-full rounded-2xl border border-dashed border-gray-300 dark:border-gray-700 p-10 text-center text-sm text-gray-600 dark:text-gray-400">
                No clients found.
              </div>
            )}
          </div>
        ))}
    </MainSkeleton>
  );
}
