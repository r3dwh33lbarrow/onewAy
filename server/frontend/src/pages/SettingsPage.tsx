import { Button, Label, TextInput, ToggleSwitch } from "flowbite-react";
import { useEffect, useMemo, useState } from "react";
import { HiOutlineCamera } from "react-icons/hi";

import { apiClient, isApiError } from "../apiClient";
import MainSkeleton from "../components/MainSkeleton";
import type { BasicTaskResponse } from "../schemas/general";
import type { UserInfoResponse, UserUpdateRequest } from "../schemas/user";
import { useErrorStore } from "../stores/errorStore.ts";
import { useAvatarStore } from "../stores/useAvatarStore.ts";
import { useTheme } from "../themes/ThemeProvider.tsx";

export default function SettingsPage() {
  const [status, setStatus] = useState<string | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [username, setUsername] = useState<string>("");
  const [initialUsername, setInitialUsername] = useState<string>("");
  const [createdAt, setCreatedAt] = useState<string>("");
  const [lastLogin, setLastLogin] = useState<string>("");
  const [localAvatarUrl, setLocalAvatarUrl] = useState<string | null>(null);

  const { addError, anyErrors } = useErrorStore();
  const { fetchAvatar } = useAvatarStore();

  const { isDark, setIsDark } = useTheme();

  const dirty = useMemo(
    () => username.trim() !== initialUsername.trim(),
    [username, initialUsername],
  );

  useEffect(() => {
    let avatarUrl: string | null = null;

    const fetchUserData = async () => {
      setStatus(null);
      const userResp = await apiClient.get<UserInfoResponse>("/user/me");
      if (isApiError(userResp)) {
        addError(userResp.detail || userResp.message);
        return;
      }
      setUsername(userResp.username);
      setInitialUsername(userResp.username);
      setCreatedAt(userResp.created_at);
      setLastLogin(userResp.last_login);

      const avatarData = await apiClient.requestBytes("/user/avatar", {
        method: "GET",
      });
      if (!isApiError(avatarData)) {
        const blob = new Blob([avatarData], { type: "image/png" });
        avatarUrl = URL.createObjectURL(blob);
        setLocalAvatarUrl(avatarUrl);
      }
    };

    fetchUserData().catch((e) => {
      addError(e instanceof Error ? e.message : "Failed to fetch user data");
    });

    return () => {
      if (avatarUrl) URL.revokeObjectURL(avatarUrl);
    };
  }, [addError]);

  const changeAvatar = () => {
    // TODO: Integrate with apiClient
    setStatus(null);
    const fileInput = document.createElement("input");
    fileInput.type = "file";
    fileInput.accept = "image/png";
    fileInput.onchange = async (e) => {
      const file = (e.target as HTMLInputElement).files?.[0];
      if (!file) {
        addError("No file selected");
        return;
      }

      try {
        const baseUrl = apiClient.getApiUrl();
        if (!baseUrl) {
          addError("API URL not configured");
          return;
        }
        const formData = new FormData();
        formData.append("file", file);
        const response = await fetch(`${baseUrl}/user/avatar`, {
          method: "PUT",
          body: formData,
          credentials: "include",
        });
        if (!response.ok) {
          const err = await response.json().catch(() => ({}));
          // noinspection ExceptionCaughtLocallyJS
          throw new Error(err.detail || response.statusText);
        }
        const avatarData = await apiClient.requestBytes("/user/avatar", {
          method: "GET",
        });
        if (isApiError(avatarData)) {
          setStatus("Avatar updated, but failed to refresh preview.");
          return;
        }
        const blob = new Blob([avatarData], { type: "image/png" });
        const url = URL.createObjectURL(blob);
        if (localAvatarUrl) URL.revokeObjectURL(localAvatarUrl);
        setLocalAvatarUrl(url);
        await fetchAvatar();
        setStatus("Avatar updated successfully.");
      } catch (e) {
        addError(e instanceof Error ? e.message : "Failed to update avatar");
      }
    };

    fileInput.click();
  };

  const saveSettings = async () => {
    setLoading(true);
    setStatus(null);
    const payload: UserUpdateRequest = { username: username.trim() };
    const resp = await apiClient.put<UserUpdateRequest, BasicTaskResponse>(
      "/user/me",
      payload,
    );
    setLoading(false);
    if (isApiError(resp)) {
      addError(resp.detail || resp.message);
      return;
    }
    setInitialUsername(username.trim());
    setStatus("Settings saved.");
  };

  return (
    <MainSkeleton baseName="Settings">
      {!anyErrors() && (
        <div className="flex min-h-[60vh] w-full">
          <div className="flex flex-col gap-4 w-full">
            {status && (
              <div className="bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg p-3 text-sm text-green-800 dark:text-green-200">
                {status}
              </div>
            )}

            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              <div className="md:col-span-1">
                <div className="rounded-xl border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 p-4 flex flex-col items-center gap-3">
                  <button
                    className="relative flex items-center justify-center w-32 h-32 hover:cursor-pointer group overflow-hidden rounded-lg border border-gray-200 dark:border-gray-800"
                    onClick={changeAvatar}
                    aria-label="Change avatar"
                  >
                    {localAvatarUrl ? (
                      <>
                        <img
                          src={localAvatarUrl}
                          alt="User Avatar"
                          className="w-full h-full object-cover"
                        />
                        <div className="absolute inset-0 bg-black/0 group-hover:bg-black/50 transition-colors duration-200 flex items-center justify-center">
                          <HiOutlineCamera className="text-white text-3xl opacity-0 group-hover:opacity-100 transition-opacity duration-200" />
                        </div>
                      </>
                    ) : (
                      <div className="w-full h-full flex items-center justify-center text-sm text-gray-400">
                        No avatar
                      </div>
                    )}
                  </button>
                  <div className="w-full">
                    <div className="mb-2 block">
                      <Label htmlFor="username">Username</Label>
                    </div>
                    <TextInput
                      id="username"
                      value={username}
                      onChange={(e) => setUsername(e.target.value)}
                    />
                  </div>
                </div>
              </div>

              <div className="md:col-span-2">
                <div className="rounded-xl border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 p-4">
                  <h2 className="text-base font-semibold text-gray-900 dark:text-gray-100 mb-4">
                    Account
                  </h2>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div>
                      <div className="text-sm text-gray-500 dark:text-gray-400">
                        Created
                      </div>
                      <div className="text-sm text-gray-900 dark:text-gray-100">
                        {createdAt ? new Date(createdAt).toLocaleString() : "—"}
                      </div>
                    </div>
                    <div>
                      <div className="text-sm text-gray-500 dark:text-gray-400">
                        Last Login
                      </div>
                      <div className="text-sm text-gray-900 dark:text-gray-100">
                        {lastLogin ? new Date(lastLogin).toLocaleString() : "—"}
                      </div>
                    </div>
                  </div>
                  <div className="mt-4 text-sm text-gray-500 dark:text-gray-400">
                    Manage your profile information and avatar. Username must be
                    unique.
                  </div>
                </div>

                <div className="rounded-xl border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 p-4 mt-6">
                  <h2 className="text-base font-semibold text-gray-900 dark:text-gray-100 mb-4">
                    Theme
                  </h2>
                  <div className="flex gap-4">
                    <p
                      className={
                        !isDark
                          ? "text-sm font-bold text-gray-500 dark:text-gray-400"
                          : "text-sm text-gray-500 dark:text-gray-400"
                      }
                    >
                      Light
                    </p>
                    <ToggleSwitch checked={isDark} onChange={setIsDark} />
                    <p
                      className={
                        isDark
                          ? "text-sm font-bold text-gray-500 dark:text-gray-400"
                          : "text-sm text-gray-500 dark:text-gray-400"
                      }
                    >
                      Dark
                    </p>
                  </div>
                </div>
              </div>
            </div>

            <div className="flex items-center justify-start gap-3">
              <Button
                color="blue"
                size="lg"
                onClick={saveSettings}
                disabled={loading || !dirty}
              >
                {loading ? "Saving..." : "Save changes"}
              </Button>
              {dirty && !loading && (
                <span className="text-sm text-gray-500 dark:text-gray-400">
                  Unsaved changes
                </span>
              )}
            </div>
          </div>
        </div>
      )}
    </MainSkeleton>
  );
}
