import { useState, useEffect, useRef, useCallback } from "react";
import { useNavigate } from "react-router-dom";

import { apiClient, isApiError } from "../apiClient";
import ClientCard from "../components/ClientCard";
import MainSkeleton from "../components/MainSkeleton";
import type { ClientAllResponse, BasicClientInfo } from "../schemas/client";
import { useErrorStore } from "../stores/errorStore.ts";
import { apiErrorToString } from "../utils.ts";

export default function Dashboard() {
  const [loading, setLoading] = useState(true);
  const [clients, setClients] = useState<BasicClientInfo[]>([]);
  const { addError, anyErrors } = useErrorStore();
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
    [addError],
  );

  useEffect(() => {
    const fetchClients = async () => {
      try {
        const response =
          await apiClient.get<ClientAllResponse>("/client/get-all");
        if (isApiError(response)) {
          if (response.statusCode === 401) {
            navigate("/login");
            return;
          }

          addError(
            `Failed to fetch clients (${response.statusCode}): ${response.detail || response.message}`,
          );
        } else {
          setClients(response.clients);
        }

        setLoading(false);
      } catch (error) {
        addError(`Failed to fetch clients: ${error}`);
        setLoading(false);
      }
    };

    fetchClients();
  }, [navigate, addError]);

  useEffect(() => {
    apiClient.startWebSocket(socketRef, onMessage, (error) =>
      addError(apiErrorToString(error)),
    );

    return () => {
      apiClient.removeWebSocketListener(onMessage);
    };
  }, [onMessage, addError]);

  return (
    <MainSkeleton baseName="Dashboard">
      {!anyErrors() &&
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
