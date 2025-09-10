import { useState, useEffect } from "react";
import { apiClient, isApiError } from "../apiClient";
import MainSkeleton from "../components/MainSkeleton.tsx";
import {snakeCaseToDashCase, snakeCaseToTitle} from "../utils.ts";

interface ModulePageProps {
  name: string;
}

interface ModuleInfo {
  name: string;
  description?: string;
  version: string;
  binaries: Record<string, string>;
}

export default function ModulePage({ name }: ModulePageProps) {
  const [moduleInfo, setModuleInfo] = useState<ModuleInfo | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchModuleInfo = async () => {
      const response = await apiClient.get<ModuleInfo>("/user/modules/get/" + snakeCaseToDashCase(name));
      if (isApiError(response)) {
        setError(`Failed to fetch module info (${response.statusCode}): ${response.detail}`);
        return
      }

      setModuleInfo(response);
    }

    fetchModuleInfo();
  }, [name]);

  return (
    <MainSkeleton baseName={"Module " + snakeCaseToTitle(name)}>
      {error && <p>{error}</p>}
      {moduleInfo && (
        <div className="flex flex-col items-center justify-center">
          <p>{moduleInfo.name}</p>
          <p>{moduleInfo.description}</p>
          <p>{moduleInfo.version}</p>
          <p>{JSON.stringify(moduleInfo.binaries)}</p>
        </div>
      )}
    </MainSkeleton>
  );
}