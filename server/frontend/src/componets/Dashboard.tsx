import { useState, useEffect, useRef } from "react";
import { useNavigate } from "react-router-dom";
import MainSidebar from "./MainSidebar";
import TopIcons from "./TopIcons";
import ClientCard from "./ClientCard";
import { apiClient } from "../apiClient";
import type { ClientAllResponse, BasicClientInfo } from "../schemas/client";
import type { TokenResponse } from "../schemas/authentication";

export default function Dashboard() {
  const [loading, setLoading] = useState(true);
  const [clients, setClients] = useState<BasicClientInfo[]>([]);
  const navigate = useNavigate();
  const socketRef = useRef<WebSocket | null>(null);

  // Function to update a specific client's alive status
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
        if ('statusCode' in response) {
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
    // Get WebSocket token and initialize connection
    const initializeWebSocket = async () => {
      try {
        const tokenResponse = await apiClient.post<object, TokenResponse>("/ws-token", {});
        if ('statusCode' in tokenResponse) {
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
            console.log("WebSocket message:", event.data);
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
          // Optionally implement reconnection logic here
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
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      <aside className="fixed inset-y-0 flex w-64 flex-col border-r border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900">
        <MainSidebar onNavigate={() => {}} />
      </aside>

      <div className="pl-64">
        <header className="sticky top-0 z-30 flex h-16 items-center justify-between gap-3 border-b border-gray-200 bg-white/80 backdrop-blur-sm dark:border-gray-800 dark:bg-gray-900/80 px-6">
          <div className="flex items-center gap-3">
            <h1 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
              Dashboard
            </h1>
          </div>

          <TopIcons />
        </header>

        <main className="p-6">
          {loading ? (
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
          )}
        </main>
      </div>
    </div>
  );
}