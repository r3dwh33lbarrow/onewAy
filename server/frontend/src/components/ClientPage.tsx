import MainSkeleton from "./MainSkeleton.tsx";
import {useEffect} from "react";
import {apiClient, isApiError} from "../apiClient.ts";
import type {ClientInfo} from "../schemas/client.ts";
import {useNavigate} from "react-router-dom";

interface ClientPageProps {
  username: string;
}

export default function ClientPage({ username }: ClientPageProps) {
  const navigate = useNavigate();

  useEffect(() => {
    const fetchClientInfo = async() => {
      const response = await apiClient.get<ClientInfo>("/client/" + username);

      if (isApiError(response)) {
        if (response.statusCode === 404) {
          navigate("/404")
        }

        return;
      }
    };

    fetchClientInfo();
  }, [username, navigate]);

  const clientPageContents = <div>Hello World</div>
  return <MainSkeleton baseName={"Client " + username} baseContents={clientPageContents} />;
}