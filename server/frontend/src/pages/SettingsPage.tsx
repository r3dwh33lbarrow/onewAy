import {useEffect, useState} from "react";
import MainSkeleton from "../components/MainSkeleton.tsx";
import {apiClient, isApiError} from "../apiClient.ts";
import { HiOutlineCamera } from "react-icons/hi";


export default function SettingsPage() {
  const [avatarUrl, setAvatarUrl] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchUserIcon = async () => {
      setError(null);
      const avatarData = await apiClient.requestBytes("/user/get-avatar",
        { method: "GET", });

      if (isApiError(avatarData)) {
        setError(`Failed to fetch user icon (${avatarData.statusCode}): ${avatarData.detail}`);
        return;
      }

      const blob = new Blob([avatarData], { type: "image/png" });
      const url = URL.createObjectURL(blob);
      setAvatarUrl(url);

      return () => URL.revokeObjectURL(url);
    };

    fetchUserIcon();
  }, []);

  const changeAvatar = () => {
    const fileInput = document.createElement("input");
    fileInput.type = "file";
    fileInput.accept = "image/png";
    fileInput.onchange = async (e) => {
      const file = (e.target as HTMLInputElement).files?.[0];
      if (!file) {
        setError("No file selected");
      }
    }

    fileInput.click();
  }

  return (
    <MainSkeleton baseName="Settings">
      {!(error) ? (
        <div className="flex min-h-[60vh] gap-4">
          <div className="flex flex-col items-center min-h-[60vh] gap-4 pt-3 w-full">
            <button className="relative flex items-center justify-center p-2 w-32 h-32 hover:cursor-pointer group overflow-hidden rounded-lg" onClick={changeAvatar}>
              {avatarUrl ? (
                <>
                  <img src={avatarUrl} alt="User Avatar" className="w-full h-full object-cover" />
                  <div className="absolute inset-0 bg-black opacity-0 group-hover:opacity-50 transition-opacity duration-200 flex items-center justify-center">
                    <HiOutlineCamera className="text-white text-3xl opacity-0 group-hover:opacity-100 transition-opacity duration-200" />
                  </div>
                </>
              ) : <></>}
            </button>
            <p className="self-start">Name</p>
          </div>
        </div>
      ) : (
        <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-3">
          <p className="text-red-800 dark:text-red-200">{error}</p>
        </div>
      )}
    </MainSkeleton>
  );
}