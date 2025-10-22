import { Button, Spinner } from "flowbite-react";
import { useCallback, useEffect, useState } from "react";
import { HiOutlineDownload } from "react-icons/hi";

import { apiClient, isApiError } from "../apiClient.ts";
import MainSkeleton from "../components/MainSkeleton.tsx";
import ModuleTable from "../components/ModuleTable.tsx";
import type { BasicTaskResponse } from "../schemas/general.ts";
import { useErrorStore } from "../stores/errorStore.ts";
import { generatePassword } from "../utils.ts";

export default function ClientBuilder() {
  const [ip, setIp] = useState("");
  const [port, setPort] = useState("");
  const [username, setUsername] = useState("");
  const [passwordLength, setPasswordLength] = useState(15);
  const [password, setPassword] = useState(generatePassword(15));
  const [platform, setPlatform] = useState<"windows" | "mac">("windows");
  const [selectedModules, setSelectedModules] = useState<
    Record<string, boolean>
  >({});
  const [rustInstalled, setRustInstalled] = useState<boolean | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const { anyErrors, addError } = useErrorStore();
  const passwordLengthSecure = password.length >= 12;

  const onSubmit = useCallback(async () => {
    if (rustInstalled === false) {
      addError("Rust is not installed on the server. Cannot generate client.");
      return;
    }

    const trimmedIp = ip.trim();
    const trimmedUsername = username.trim();
    const trimmedPassword = password.trim();
    const portNumber = Number(port);

    if (!trimmedIp || !port || !trimmedUsername || !trimmedPassword) {
      addError("All fields are required before generating a client.");
      return;
    }

    if (!Number.isInteger(portNumber) || portNumber < 1 || portNumber > 65535) {
      addError("Port must be an integer between 1 and 65535.");
      return;
    }

    const modules = Object.entries(selectedModules)
      .filter(([, value]) => value)
      .map(([key]) => key);

    setIsSubmitting(true);
    try {
      const response = await apiClient.requestBytes("/user/generate-client", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          platform,
          ip_address: trimmedIp,
          port: portNumber,
          username: trimmedUsername,
          password: trimmedPassword,
          packaged_modules: modules,
        }),
      });

      if (isApiError(response)) {
        addError(
          `Failed to generate client (${response.statusCode}): ${response.detail || response.message}`,
        );
        return;
      }

      const blob = new Blob([response], { type: "application/zip" });
      const downloadUrl = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = downloadUrl;
      const safeUsername = trimmedUsername || "client";
      link.download = `${safeUsername}-bundle.zip`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(downloadUrl);
    } catch (error) {
      addError(
        error instanceof Error
          ? error.message
          : "Unexpected error while generating client.",
      );
    } finally {
      setIsSubmitting(false);
    }
  }, [
    addError,
    ip,
    password,
    platform,
    port,
    rustInstalled,
    selectedModules,
    username,
  ]);

  useEffect(() => {
    const apiUrl = apiClient.getApiUrl();
    if (apiUrl) {
      try {
        const url = new URL(apiUrl);
        const hostname =
          url.hostname === "localhost" ? "127.0.0.1" : url.hostname;
        setIp(hostname);
        const derivedPort =
          url.port ||
          (url.protocol === "https:"
            ? "443"
            : url.protocol === "http:"
              ? "80"
              : "");
        if (derivedPort) {
          setPort(derivedPort);
        }
      } catch (error) {
        addError("Failed to parse API URL: " + error);
      }
    }
  }, [addError]);

  useEffect(() => {
    const checkRustInstalled = async () => {
      setRustInstalled(null);
      const response =
        await apiClient.get<BasicTaskResponse>("/user/verify-rust");
      if (isApiError(response)) {
        addError(
          `Failed to verify Rust installation (${response.statusCode}): ${response.detail || response.message}`,
        );
      } else {
        if (response.result !== "success") {
          setRustInstalled(false);
        } else {
          setRustInstalled(true);
        }
      }
    };

    checkRustInstalled();
  }, [addError]);

  return (
    <MainSkeleton baseName="Client Builder">
      <div className="flex justify-between items-center mb-1">
        <p className="font-bold dark:text-gray-400 px-2">Configuration</p>
        {rustInstalled === null ? (
          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-300 text-gray-800 dark:bg-gray-700 dark:text-gray-200">
            Loading...
          </span>
        ) : rustInstalled ? (
          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-300 text-green-800 dark:bg-green-900 dark:text-green-200">
            Rust installed on server
          </span>
        ) : (
          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-red-300 text-red-800 dark:bg-red-900 dark:text-red-200">
            Rust not installed on server
          </span>
        )}
      </div>

      <div className="h-full rounded-2xl shadow-xl bg-white dark:bg-gray-800 p-4">
        <div className="grid grid-cols-[max-content_1fr] items-center gap-x-4 gap-y-2">
          <p>IP Address:</p>
          <input
            type="text"
            placeholder="x.x.x.x"
            className="border border-gray-300 rounded-lg px-4 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:text-gray-300 dark:border-gray-600"
            value={ip}
            onChange={(e) => setIp(e.target.value)}
          />

          <p>Port:</p>
          <input
            type="text"
            placeholder="0-65535"
            className="border border-gray-300 rounded-lg px-4 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:text-gray-300 dark:border-gray-600"
            value={port}
            onChange={(e) => setPort(e.target.value)}
          />

          <p>Platform:</p>
          <select
            className="border border-gray-300 rounded-lg px-4 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:text-gray-300 dark:border-gray-600"
            value={platform}
            onChange={(e) => setPlatform(e.target.value as "windows" | "mac")}
          >
            <option value="windows">Windows</option>
            <option value="mac">macOS</option>
          </select>

          <p>Username:</p>
          <input
            type="text"
            className="border border-gray-300 rounded-lg px-4 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:text-gray-300 dark:border-gray-600"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
          />

          <p>Password:</p>
          <input
            type="text"
            className="border border-gray-300 rounded-lg px-4 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:text-gray-300 dark:border-gray-600"
            value={password}
            onChange={(e) => {
              const value = e.target.value;
              setPassword(value);
              setPasswordLength(value.length);
            }}
          />

          <p className="self-center">Password length:</p>
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2 w-1/2">
              <input
                type="range"
                min={1}
                max={100}
                value={passwordLength}
                className="w-full"
                onChange={(event) => {
                  const length = Number(event.target.value);
                  setPasswordLength(length);
                  setPassword(generatePassword(length));
                  setPasswordLength(length);
                }}
              />
              <span className="text-sm text-gray-600 dark:text-gray-300">
                {passwordLength}
              </span>
            </div>
            <span
              className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                passwordLengthSecure
                  ? "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200"
                  : "bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200"
              }`}
            >
              {passwordLengthSecure
                ? "Secure password length"
                : "Insecure password length"}
            </span>
          </div>
        </div>
      </div>

      <p className="font-bold dark:text-gray-400 px-2 mt-6">
        Available Modules to Package
      </p>
      <ModuleTable onModuleTick={setSelectedModules} marginTop="mt-1" />

      <div className="flex justify-end mt-4">
        <Button
          color="indigo"
          className="px-6 gap-1"
          pill
          aria-label="Download client"
          disabled={isSubmitting || rustInstalled === false}
          onClick={() => void onSubmit()}
        >
          {isSubmitting ? (
            <>
              <Spinner size="sm" light />
              Generating...
            </>
          ) : (
            <>
              <HiOutlineDownload className="h-5 w-5" />
              Download Client
            </>
          )}
        </Button>
      </div>
    </MainSkeleton>
  );
}
