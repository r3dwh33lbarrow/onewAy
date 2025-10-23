import { Alert, Badge, Button, Spinner } from "flowbite-react";
import { useCallback, useEffect, useState } from "react";
import { HiOutlineDownload } from "react-icons/hi";
import { HiInformationCircle } from "react-icons/hi";

import { apiClient, isApiError } from "../apiClient.ts";
import MainSkeleton from "../components/MainSkeleton.tsx";
import ModuleTable from "../components/ModuleTable.tsx";
import { useErrorStore } from "../stores/errorStore.ts";
import { generatePassword } from "../utils.ts";
import type { VerifyRustResponse } from "../schemas/userGenerateClient.ts";

export default function ClientBuilder() {
  const [ip, setIp] = useState("");
  const [port, setPort] = useState("");
  const [username, setUsername] = useState("");
  const [passwordLength, setPasswordLength] = useState(15);
  const [password, setPassword] = useState(generatePassword(15));
  const [platform, setPlatform] = useState<"windows" | "mac" | "linux">(
    "windows",
  );
  const [selectedModules, setSelectedModules] = useState<
    Record<string, boolean>
  >({});
  const [rustTargets, setRustTargets] = useState<VerifyRustResponse | null>(
    null,
  );
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [outputOverride, setOutputOverride] = useState(false);
  const [debug, setDebug] = useState(false);

  const { anyErrors, addError } = useErrorStore();
  const passwordLengthSecure = password.length >= 12;
  const rustInstalled = rustTargets?.rust_installed ?? null;
  const windowsTargetInstalled = rustTargets?.windows_target_installed ?? false;
  const macTargetInstalled = rustTargets?.mac_target_installed ?? false;
  const linuxTargetInstalled = rustTargets?.linux_target_installed ?? false;

  const onSubmit = useCallback(async () => {
    if (rustInstalled === false) {
      addError("Rust is not installed on the server. Cannot generate client.");
      return;
    }

    if (platform === "windows" && !windowsTargetInstalled) {
      addError("Windows Rust target is not installed on the server.");
      return;
    }
    if (platform === "mac" && !macTargetInstalled) {
      addError("macOS Rust target is not installed on the server.");
      return;
    }
    if (platform === "linux" && !linuxTargetInstalled) {
      addError("Linux Rust target is not installed on the server.");
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
          output_override: outputOverride,
          debug: debug,
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
    windowsTargetInstalled,
    macTargetInstalled,
    linuxTargetInstalled,
    selectedModules,
    username,
    outputOverride,
    debug,
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
      setRustTargets(null);
      const response = await apiClient.get<VerifyRustResponse>(
        "/user/verify-rust",
      );
      if (isApiError(response)) {
        addError(
          `Failed to verify Rust installation (${response.statusCode}): ${response.detail || response.message}`,
        );
      } else {
        setRustTargets(response);
      }
    };

    void checkRustInstalled();
  }, [addError]);

  return (
    <MainSkeleton baseName="Client Builder">
      {outputOverride && (
        <Alert color="warning" icon={HiInformationCircle} className="mb-4">
          <span className="font-medium">Output override enabled!</span> Output
          override will make the client output to stdout for logging purposes.
          If you want a silent client do not click this option.
        </Alert>
      )}

      <div className="flex justify-between items-center mb-1">
        <p className="font-bold dark:text-gray-400 px-2">Configuration</p>
        <div className="flex flex-wrap gap-2">
          {rustInstalled === null ? (
            <Badge color="info">Detecting toolchain…</Badge>
          ) : rustInstalled ? (
            <Badge color="success">Rust toolchain available</Badge>
          ) : (
            <Badge color="failure">Rust toolchain missing</Badge>
          )}
          <Badge color={windowsTargetInstalled ? "success" : "failure"}>
            Windows target
          </Badge>
          <Badge color={macTargetInstalled ? "success" : "failure"}>
            macOS target
          </Badge>
          <Badge color={linuxTargetInstalled ? "success" : "failure"}>
            Linux target
          </Badge>
        </div>
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
            onChange={(e) =>
              setPlatform(e.target.value as "windows" | "mac" | "linux")
            }
          >
            <option value="windows">Windows</option>
            <option value="mac">macOS</option>
            <option value="linux">Linux</option>
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

          <p>Options:</p>
          <div className="flex items-center gap-6">
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={outputOverride}
                onChange={(e) => {
                  const checked = e.target.checked;
                  setOutputOverride(checked);
                  if (!checked) {
                    setDebug(false);
                  }
                }}
                className="w-4 h-4 text-blue-600 bg-gray-100 border-gray-300 rounded focus:ring-blue-500 dark:focus:ring-blue-600 dark:ring-offset-gray-800 focus:ring-2 dark:bg-gray-700 dark:border-gray-600"
              />
              <span className="text-sm text-gray-900 dark:text-gray-300">
                Output override
              </span>
            </label>
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={debug}
                onChange={(e) => {
                  const checked = e.target.checked;
                  setDebug(checked);
                  // If checking debug, also check output override
                  if (checked) {
                    setOutputOverride(true);
                  }
                }}
                className="w-4 h-4 text-blue-600 bg-gray-100 border-gray-300 rounded focus:ring-blue-500 dark:focus:ring-blue-600 dark:ring-offset-gray-800 focus:ring-2 dark:bg-gray-700 dark:border-gray-600"
              />
              <span className="text-sm text-gray-900 dark:text-gray-300">
                Debug
              </span>
            </label>
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
