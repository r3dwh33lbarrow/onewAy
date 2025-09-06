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
        {clientInfo ? <p>{clientInfo.uuid}</p> : <p>Loading...</p>}
      </div>
    </MainSkeleton>
  );
}