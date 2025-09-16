import { useEffect, useMemo, useRef, useState } from "react";
import MainSkeleton from "../components/MainSkeleton.tsx";
import { apiClient, isApiError } from "../apiClient.ts";
import { HiOutlineCamera } from "react-icons/hi";
import { Button, Label, TextInput } from "flowbite-react";
import type { UserInfoResponse, UserUpdateRequest } from "../schemas/user.ts";
import type { BasicTaskResponse } from "../schemas/general.ts";


export default function SettingsPage() {
  const [avatarUrl, setAvatarUrl] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [status, setStatus] = useState<string | null>(null);
  const [loading, setLoading] = useState<boolean>(false);

  const [username, setUsername] = useState<string>("");
  const [initialUsername, setInitialUsername] = useState<string>("");
  const [createdAt, setCreatedAt] = useState<string>("");
  const [lastLogin, setLastLogin] = useState<string>("");
  const avatarUrlRef = useRef<string | null>(null);

  const dirty = useMemo(() => username.trim() !== initialUsername.trim(), [username, initialUsername]);

  useEffect(() => {
    const fetchUserData = async () => {
      setError(null);
      setStatus(null);
      const userResp = await apiClient.get<UserInfoResponse>("/user/me");
      if (isApiError(userResp)) {
        setError(userResp.detail || userResp.message);
        return;
      }
      setUsername(userResp.username);
      setInitialUsername(userResp.username);
      setCreatedAt(userResp.created_at);
      setLastLogin(userResp.last_login);

      const avatarData = await apiClient.requestBytes("/user/get-avatar", { method: "GET" });
      if (!isApiError(avatarData)) {
        const blob = new Blob([avatarData], { type: "image/png" });
        const url = URL.createObjectURL(blob);
        if (avatarUrlRef.current) URL.revokeObjectURL(avatarUrlRef.current);
        avatarUrlRef.current = url;
        setAvatarUrl(url);
      }
    };

    fetchUserData();
    return () => {
      if (avatarUrlRef.current) URL.revokeObjectURL(avatarUrlRef.current);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const changeAvatar = () => {
    setError(null);
    setStatus(null);
    const fileInput = document.createElement("input");
    fileInput.type = "file";
    fileInput.accept = "image/png";
    fileInput.onchange = async (e) => {
      const file = (e.target as HTMLInputElement).files?.[0];
      if (!file) {
        setError("No file selected");
        return;
      }

      try {
        const baseUrl = apiClient.getApiUrl();
        if (!baseUrl) {
          setError("API URL not configured");
          return;
        }
        const formData = new FormData();
        formData.append("file", file);
        const response = await fetch(`${baseUrl}/user/update-avatar`, {
          method: "POST",
          body: formData,
          credentials: "include",
        });
        if (!response.ok) {
          const err = await response.json().catch(() => ({}));
          throw new Error(err.detail || response.statusText);
        }
        // Refresh avatar
        const avatarData = await apiClient.requestBytes("/user/get-avatar", { method: "GET" });
        if (isApiError(avatarData)) {
          setStatus("Avatar updated, but failed to refresh preview.");
          return;
        }
        const blob = new Blob([avatarData], { type: "image/png" });
        const url = URL.createObjectURL(blob);
        if (avatarUrlRef.current) URL.revokeObjectURL(avatarUrlRef.current);
        avatarUrlRef.current = url;
        setAvatarUrl(url);
        setStatus("Avatar updated successfully.");
      } catch (e) {
        setError(e instanceof Error ? e.message : "Failed to update avatar");
      }
    };

    fileInput.click();
  };

  const saveSettings = async () => {
    setLoading(true);
    setError(null);
    setStatus(null);
    const payload: UserUpdateRequest = { username: username.trim() };
    const resp = await apiClient.put<UserUpdateRequest, BasicTaskResponse>("/user/me", payload);
    setLoading(false);
    if (isApiError(resp)) {
      setError(resp.detail || resp.message);
      return;
    }
    setInitialUsername(username.trim());
    setStatus("Settings saved.");
  };

  return (
    <MainSkeleton baseName="Settings">
      {!error ? (
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
                    {avatarUrl ? (
                      <>
                        <img src={avatarUrl} alt="User Avatar" className="w-full h-full object-cover" />
                        <div className="absolute inset-0 bg-black/0 group-hover:bg-black/50 transition-colors duration-200 flex items-center justify-center">
                          <HiOutlineCamera className="text-white text-3xl opacity-0 group-hover:opacity-100 transition-opacity duration-200" />
                        </div>
                      </>
                    ) : (
                      <div className="w-full h-full flex items-center justify-center text-sm text-gray-400">No avatar</div>
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
                  <h2 className="text-base font-semibold text-gray-900 dark:text-gray-100 mb-4">Account</h2>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div>
                      <div className="text-sm text-gray-500 dark:text-gray-400">Created</div>
                      <div className="text-sm text-gray-900 dark:text-gray-100">
                        {createdAt ? new Date(createdAt).toLocaleString() : "—"}
                      </div>
                    </div>
                    <div>
                      <div className="text-sm text-gray-500 dark:text-gray-400">Last Login</div>
                      <div className="text-sm text-gray-900 dark:text-gray-100">
                        {lastLogin ? new Date(lastLogin).toLocaleString() : "—"}
                      </div>
                    </div>
                  </div>
                  <div className="mt-4 text-sm text-gray-500 dark:text-gray-400">
                    Manage your profile information and avatar. Username must be unique.
                  </div>
                </div>
              </div>
            </div>

            <div className="flex items-center justify-start gap-3">
              <Button color="blue" size="lg" onClick={saveSettings} disabled={loading || !dirty}>
                {loading ? "Saving..." : "Save changes"}
              </Button>
              {dirty && !loading && (
                <span className="text-sm text-gray-500 dark:text-gray-400">Unsaved changes</span>
              )}
            </div>
          </div>
        </div>
      ) : (
        <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-3">
          <div className="text-red-800 dark:text-red-200">{error}</div>
        </div>
      )}
    </MainSkeleton>
  );
}
