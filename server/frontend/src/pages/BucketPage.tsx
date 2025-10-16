import { Button } from "flowbite-react";
import { useEffect, useState } from "react";
import { HiOutlineTrash } from "react-icons/hi";
import { useNavigate, useParams } from "react-router-dom";

import { apiClient, isApiError } from "../apiClient.ts";
import MainSkeleton from "../components/MainSkeleton.tsx";
import type { BasicTaskResponse } from "../schemas/general.ts";
import type {AllBucketsResponse, BucketData} from "../schemas/module_bucket.ts";
import { snakeCaseToTitle } from "../utils.ts";

export function BucketPage() {
  const navigate = useNavigate();
  const module = useParams<{ module: string }>();

  const [error, setError] = useState<string | null>(null);
  const [bucketData, setBucketData] = useState<string | null>(null);

  const deleteBucket = async () => {
    if (!module.module) return;
    const response = await apiClient.delete<BasicTaskResponse>(
      `/module/bucket?module_name=${module.module}`,
    );
    if (isApiError(response)) {
      setError(
        `Failed to delete bucket (${response.statusCode}): ${response.detail || response.message}`,
      );
      return;
    }

    navigate("/dashboard");
  };

  useEffect(() => {
    if (!module.module) return;
    const getBucket = async () => {
      const response = await apiClient.get<BucketData>(
        `/module/bucket?module_name=${module.module}`,
      );
      if (isApiError(response)) {
        setError(
          `Failed to fetch bucket (${response.statusCode}): ${response.detail || response.message}`,
        );
        return;
      }

      setBucketData(response.data);
    };

    getBucket();
  }, [module]);

  return (
    <MainSkeleton
      baseName={
        module?.module ? "Bucket for " + snakeCaseToTitle(module.module) : "N/A"
      }
    >
      {error && (
        <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-3 mb-2">
          <p className="text-red-800 dark:text-red-200">{error}</p>
        </div>
      )}

      <div className="flex flex-col h-[65vh] bg-black rounded-lg overflow-hidden">
        <div className="flex-1 overflow-auto p-3 font-mono text-sm text-white">
          {bucketData}
        </div>
      </div>
      <div className="flex justify-between mt-4">
        <p className="text-sm text-gray-500 dark:text-gray-600">
          Buckets delete 3 days after viewing.
        </p>

        <Button
          pill
          color="purple"
          className=" px-6 gap-1"
          onClick={deleteBucket}
        >
          <HiOutlineTrash className="h-5 w-5" />
          Delete
        </Button>
      </div>
    </MainSkeleton>
  );
}
