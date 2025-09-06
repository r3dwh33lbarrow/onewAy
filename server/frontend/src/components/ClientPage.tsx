import MainSkeleton from "./MainSkeleton.tsx";
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
          <div className="flex flex-col justify-center items-center text-gray-800 dark:text-gray-200 gap-2">
            <p>{clientInfo.uuid}</p>
            <p>{clientInfo.username}</p>
            <p>{clientInfo.hostname}</p>
            <p>{clientInfo.ip_address}</p>
            <p>{String(clientInfo.alive)}</p>
            <p>{clientInfo.last_contact}</p>
          </div>
        ) : (
          <p>Loading...</p>
        )}
      </div>
    </MainSkeleton>
  );
}