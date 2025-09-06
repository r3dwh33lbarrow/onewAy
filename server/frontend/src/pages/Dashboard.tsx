import { useState, useEffect, useRef } from "react";
import { useNavigate } from "react-router-dom";
import ClientCard from "../components/ClientCard.tsx";
import { apiClient } from "../apiClient.ts";
import type { ClientAllResponse, BasicClientInfo } from "../schemas/client.ts";
import type { TokenResponse } from "../schemas/authentication.ts";
import MainSkeleton from "../components/MainSkeleton.tsx";

export default function Dashboard() {
  const [loading, setLoading] = useState(true);
  const [clients, setClients] = useState<BasicClientInfo[]>([]);
  const navigate = useNavigate();
  const socketRef = useRef<WebSocket | null>(null);

  const updateClientAliveStatus = (username: string, alive: boolean) => {
    setClients(prevClients =>
      prevClients.map(client =>
        client.username === username
          ? { ...client, alive, last_contact: new Date().toISOString() }
          : client
      )
    );
  };

  useEffect(() => {
    const fetchClients = async () => {
      try {
        const response = await apiClient.get<ClientAllResponse>("/client/all");
        if ("statusCode" in response) {
          console.error("API Error:", response.message);
          navigate("/login");
          return;
        }

        setClients(response.clients);
        setLoading(false);
      } catch (error) {
        console.error("Failed to fetch clients:", error);
        setLoading(false);
      }
    };

    fetchClients();
  }, [navigate]);

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

  const dashboardContents = loading ? (
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
  );

  return (
    <MainSkeleton baseName="Dashboard">
      {dashboardContents}
    </MainSkeleton>
  );
}
