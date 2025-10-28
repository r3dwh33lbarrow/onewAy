import { Button } from "flowbite-react";
import { type JSX, useEffect, useState } from "react";
import { HiOutlineTrash } from "react-icons/hi";
import { useNavigate, useParams } from "react-router-dom";

import { apiClient, isApiError } from "../apiClient.ts";
import MainSkeleton from "../components/MainSkeleton.tsx";
import type { BasicTaskResponse } from "../schemas/general.ts";
import type { BucketData } from "../schemas/module_bucket.ts";
import { parseBucketData, type ParsedBlock } from "../services/bucket.ts";
import { useErrorStore } from "../stores/errorStore.ts";
import { useNotificationStore } from "../stores/notificationStore.ts";
import { snakeCaseToTitle } from "../utils.ts";

export function BucketPage() {
  const navigate = useNavigate();
  const module = useParams<{ module: string }>();
  const { addError } = useErrorStore();
  const { markAsConsumed } = useNotificationStore();

  const [bucketData, setBucketData] = useState<string | null>(null);
  const [parsedContent, setParsedContent] = useState<{
    lines: string[];
    blocks: ParsedBlock[];
  } | null>(null);

  const deleteBucket = async () => {
    if (!module.module) return;
    const response = await apiClient.delete<BasicTaskResponse>(
      `/module/bucket?module_name=${module.module}`,
    );
    if (isApiError(response)) {
      addError(
        `Failed to delete bucket (${response.statusCode}): ${response.detail || response.message}`,
      );
      return;
    }

    navigate("/dashboard");
  };

  useEffect(() => {
    if (!module.module) return;
    markAsConsumed(module.module);

    const getBucket = async () => {
      const response = await apiClient.get<BucketData>(
        `/module/bucket?module_name=${module.module}`,
      );
      console.log(response);
      if (isApiError(response)) {
        addError(
          `Failed to fetch bucket (${response.statusCode}): ${response.detail || response.message}`,
        );
        return;
      }

      setBucketData(response.data);

      try {
        const result = parseBucketData(response.data);
        setParsedContent({
          lines: result.cleanText.split("\n"),
          blocks: result.blocks,
        });
      } catch (error) {
        addError(
          `Failed to parse bucket data: ${error instanceof Error ? error.message : "Unknown error"}`,
        );
        setParsedContent(null);
      }
    };

    getBucket();
  }, [module, addError, markAsConsumed]);

  const renderBlock = (block: ParsedBlock) => {
    switch (block.type.toLowerCase()) {
      case "image":
      case "png":
      case "jpg":
      case "jpeg":
      case "gif":
      case "webp":
        return (
          <div className="my-4">
            <img
              src={`data:image/${block.type.toLowerCase()};base64,${block.content}`}
              alt={`Embedded ${block.type}`}
              className="w-full h-auto rounded border border-gray-700"
            />
          </div>
        );
      case "code":
        return (
          <pre className="my-4 p-3 bg-gray-900 rounded border border-gray-700 overflow-x-auto">
            <code>{block.content}</code>
          </pre>
        );
      default:
        return (
          <div className="my-4 p-3 bg-gray-800 rounded border border-gray-700">
            <div className="text-xs text-gray-400 mb-2">
              Block type: {block.type}
            </div>
            <pre className="whitespace-pre-wrap">{block.content}</pre>
          </div>
        );
    }
  };

  const renderContent = () => {
    if (!parsedContent) {
      return <div className="whitespace-pre-wrap">{bucketData}</div>;
    }

    const { lines, blocks } = parsedContent;
    const elements: JSX.Element[] = [];
    let currentLine = 0;

    const sortedBlocks = [...blocks].sort((a, b) => a.index - b.index);

    sortedBlocks.forEach((block, blockIdx) => {
      if (currentLine < block.index) {
        const textContent = lines.slice(currentLine, block.index).join("\n");
        if (textContent.trim()) {
          elements.push(
            <div key={`text-${currentLine}`} className="whitespace-pre-wrap">
              {textContent}
            </div>,
          );
        }
      }

      elements.push(<div key={`block-${blockIdx}`}>{renderBlock(block)}</div>);

      currentLine = block.index;
    });

    if (currentLine < lines.length) {
      const textContent = lines.slice(currentLine).join("\n");
      if (textContent.trim()) {
        elements.push(
          <div key={`text-${currentLine}`} className="whitespace-pre-wrap">
            {textContent}
          </div>,
        );
      }
    }

    return <>{elements}</>;
  };

  return (
    <MainSkeleton
      baseName={
        module?.module ? "Bucket for " + snakeCaseToTitle(module.module) : "N/A"
      }
    >
      <div className="flex flex-col h-[65vh] bg-black rounded-lg overflow-hidden">
        <div className="flex-1 overflow-auto p-3 font-mono text-sm text-white">
          {renderContent()}
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
