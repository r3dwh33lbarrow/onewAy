import {
  Button,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeadCell,
  TableRow,
} from "flowbite-react";
import { useCallback, useEffect, useRef, useState } from "react";
import { useParams } from "react-router-dom";

import { apiClient, isApiError } from "../apiClient";
import MainSkeleton from "../components/MainSkeleton";
import type { ClientAllInfo } from "../schemas/client";
import type { BasicTaskResponse } from "../schemas/general";
import type { UserModuleAllResponse } from "../schemas/module";
import type {
  InstalledModuleInfo,
  ModuleBasicInfo,
} from "../schemas/module.ts";
import { apiErrorToString, snakeCaseToTitle } from "../utils";

export default function ConsolePage() {
  const { username } = useParams<{ username: string }>();
  const [clientInfo, setClientInfo] = useState<ClientAllInfo | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [modules, setModules] = useState<ModuleBasicInfo[]>([]);
  const [installed, setInstalled] = useState<InstalledModuleInfo[]>([]);
  const [lines, setLines] = useState<
    { stream: "stdout" | "stderr" | "event"; text: string }[]
  >([]);
  const [inputValue, setInputValue] = useState("");
  const socketRef = useRef<WebSocket | null>(null);
  const consoleRef = useRef<HTMLDivElement | null>(null);

  const onMessage = useCallback(
    (event: MessageEvent) => {
      try {
        const data = JSON.parse(event.data);
        if (
          data.type === "console_output" &&
          data.data?.username === username
        ) {
          const line = data.data.line as string;
          const stream: "stdout" | "stderr" =
            data.data.stream === "stderr" ? "stderr" : "stdout";
          setLines((prev) => {
            const next: typeof prev = [...prev, { stream, text: line }];
            if (next.length > 2000) next.shift();
            return next;
          });
        } else if (
          data.type === "console_event" &&
          data.data?.username === username
        ) {
          const event = data.data.event as string;
          const moduleName = data.data.module_name as string;
          const code = data.data.code;
          let text = "";
          if (event === "module_started") text = `Started ${moduleName}`;
          else if (event === "module_exit")
            text = `Exited ${moduleName} with code ${code}`;
          else if (event === "module_canceled") text = `Canceled ${moduleName}`;
          if (text) {
            setLines((prev) => {
              const last = prev[prev.length - 1];
              if (last && last.stream === "event" && last.text === text) return prev;
              const next: typeof prev = [...prev, { stream: "event", text }];
              if (next.length > 2000) next.shift();
              return next;
            });
          }
        }
      } catch { /* empty */ }
    },
    [username],
  );

  useEffect(() => {
    const fetchClientInformation = async () => {
      setLoading(true);
      setError(null);
      if (!username) {
        setError("No username provided");
        setLoading(false);
        return;
      }
      const response = await apiClient.get<ClientAllInfo>(
        `/client/get/${username}`,
      );
      if (isApiError(response)) {
        setError(`Failed to fetch client information: ${response.detail}`);
        setLoading(false);
        return;
      }
      setClientInfo(response);
      setLoading(false);
    };
    fetchClientInformation();
  }, [username]);

  useEffect(() => {
    const fetchModules = async () => {
      if (!username) return;
      const allResult =
        await apiClient.get<UserModuleAllResponse>("/module/all");
      if ("modules" in allResult) setModules(allResult.modules);
      const instResult = await apiClient.get<{
        all_installed: InstalledModuleInfo[];
      }>(`/module/installed/${encodeURIComponent(username)}`);
      if ("all_installed" in instResult) setInstalled(instResult.all_installed);
    };
    fetchModules();
  }, [username]);

  useEffect(() => {
    apiClient.startWebSocket(socketRef, onMessage, (error) =>
      setError(apiErrorToString(error)),
    );
    const currentSocket = socketRef.current;
    return () => {
      currentSocket?.removeEventListener("message", onMessage);
    };
  }, [onMessage]);

  useEffect(() => {
    if (consoleRef.current) {
      consoleRef.current.scrollTop = consoleRef.current.scrollHeight;
    }
  }, [lines]);

  const isInstalled = (name: string) => installed.some((m) => m.name === name);

  const onRun = async (name: string) => {
    if (!username) return;
    const res = await apiClient.get<BasicTaskResponse>(
      `/module/run/${encodeURIComponent(name)}?client_username=${encodeURIComponent(
        username,
      )}`,
    );
    if ("statusCode" in res) alert(res.message || "Failed to run module");
  };

  const onCancel = async (name: string) => {
    if (!username) return;
    const res = await apiClient.get<BasicTaskResponse>(
      `/module/cancel/${encodeURIComponent(name)}?client_username=${encodeURIComponent(
        username,
      )}`,
    );
    if ("statusCode" in res) alert(res.message || "Failed to cancel module");
  };

  const handleInputSubmit = useCallback(() => {
    if (!inputValue.trim()) return;
    console.log("stdin:", inputValue);
    setInputValue("");
  }, [inputValue]);

  return (
    <MainSkeleton baseName={`Console for ${username ?? ""}`}>
      {loading && <div>Loading...</div>}

      {!username && (
        <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-3">
          <p className="text-red-800 dark:text-red-200">No username provided</p>
        </div>
      )}

      {error && (
        <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-3">
          <p className="text-red-800 dark:text-red-200">{error}</p>
        </div>
      )}

      {!loading && !error && clientInfo && clientInfo.alive && (
        <>
          <div className="flex flex-col h-[65vh] bg-black rounded-lg overflow-hidden">
            <div
              ref={consoleRef}
              className="flex-1 overflow-auto p-3 font-mono text-sm"
            >
              {lines.map((l, idx) => (
                <div
                  key={idx}
                  className={
                    l.stream === "stderr"
                      ? "text-red-400"
                      : l.stream === "event"
                        ? "text-yellow-300"
                        : "text-gray-100"
                  }
                >
                  {l.text}
                </div>
              ))}
            </div>
            <div className="border-t border-gray-700 p-2">
              <span className="text-green-400">$ </span>
              <input
                type="text"
                value={inputValue}
                onChange={(e) => setInputValue(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter") handleInputSubmit();
                }}
                className="bg-transparent outline-none text-gray-100 w-[calc(100%-1rem)]"
                spellCheck={false}
                autoFocus
              />
            </div>
          </div>

          <div className="bg-white dark:bg-gray-800 rounded-lg shadow mt-4">
            <Table>
              <TableHead>
                <TableRow>
                  <TableHeadCell>Module</TableHeadCell>
                  <TableHeadCell>Description</TableHeadCell>
                  <TableHeadCell>Version</TableHeadCell>
                  <TableHeadCell>Start</TableHeadCell>
                  <TableHeadCell>Actions</TableHeadCell>
                </TableRow>
              </TableHead>
              <TableBody className="divide-y">
                {modules.map((m, i) => {
                  const manual = (m.start || "").toLowerCase() === "manual";
                  const installedOnClient = isInstalled(m.name);
                  return (
                    <TableRow
                      key={`${m.name}-${i}`}
                      className="bg-white dark:border-gray-700 dark:bg-gray-800"
                    >
                      <TableCell className="whitespace-nowrap font-medium text-gray-900 dark:text-white">
                        {snakeCaseToTitle(m.name)}
                      </TableCell>
                      <TableCell className="whitespace-nowrap text-gray-900 dark:text-white">
                        {m.description}
                      </TableCell>
                      <TableCell>{m.version}</TableCell>
                      <TableCell>{m.start}</TableCell>
                      <TableCell>
                        <div className="flex gap-2">
                          <Button
                            size="xs"
                            color="indigo"
                            disabled={!manual || !installedOnClient}
                            onClick={() => onRun(m.name)}
                          >
                            Run
                          </Button>
                          <Button
                            size="xs"
                            color="failure"
                            disabled={!installedOnClient}
                            onClick={() => onCancel(m.name)}
                          >
                            Cancel
                          </Button>
                        </div>
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          </div>
        </>
      )}

      {!loading && !error && clientInfo && !clientInfo.alive && (
        <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-3">
          <p className="text-red-800 dark:text-red-200">
            Client is offline. Console is unavailable.
          </p>
        </div>
      )}
    </MainSkeleton>
  );
}
