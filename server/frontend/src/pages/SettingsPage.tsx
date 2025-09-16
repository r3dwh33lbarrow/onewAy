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

  return (
    <MainSkeleton baseName="Settings">
      <div className="flex flex-col items-center justify-center min-h-[60v] gap-4">
        <button className="relative flex items-center justify-center p-2 w-32 h-32 hover:cursor-pointer group overflow-hidden rounded-lg">
          {avatarUrl ? (
            <>
              <img src={avatarUrl} alt="User Avatar" className="w-full h-full object-cover" />
              <div className="absolute inset-0 bg-black opacity-0 group-hover:opacity-50 transition-opacity duration-200 flex items-center justify-center">
                <HiOutlineCamera className="text-white text-3xl opacity-0 group-hover:opacity-100 transition-opacity duration-200" />
              </div>
            </>
          ) : <></>}
        </button>
      </div>
    </MainSkeleton>
  );
}