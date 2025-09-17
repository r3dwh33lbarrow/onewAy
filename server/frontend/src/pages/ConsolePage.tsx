import MainSkeleton from "../components/MainSkeleton.tsx";
import {useEffect, useState} from "react";
import type { ClientAllInfo } from "../schemas/client.ts";
import { apiClient, isApiError } from "../apiClient.ts";

interface ConsolePageProps {
  username: string;
}

export default function ConsolePage({ username }: ConsolePageProps) {
  const [clientInfo, setClientInfo] = useState<ClientAllInfo | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchClientInformation = async () => {
      setLoading(true);
      setError(null);
      const response = await apiClient.get<ClientAllInfo>(`/client/get/${username}`);

      if (isApiError(response)) {
        setError(`Failed to fetch client information: ${response.detail}`);
        setLoading(false);
        return;
      }

      setClientInfo(response);
      setLoading(false);
    }

    fetchClientInformation();
  }, [username]);

  return (
    <MainSkeleton baseName={`Console for ${username}`}>
      {loading && (
        <div>Loading...</div>
      )}

      {error && (
        <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-3">
          <p className="text-red-800 dark:text-red-200">{error}</p>
        </div>
      )}

      {!loading && !error && clientInfo && clientInfo.alive && (
        <>
          <div className="w-full h-[62.5vh] bg-black rounded-lg">
            {/* Console content will go here */}
          </div>
          <p>hello world</p>
        </>
      )}
    </MainSkeleton>
  );
}