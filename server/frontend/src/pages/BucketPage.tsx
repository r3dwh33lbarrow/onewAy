import { Button } from "flowbite-react";
import { type JSX, useEffect, useMemo, useState } from "react";
import { HiOutlineTrash } from "react-icons/hi";
import { useNavigate, useParams } from "react-router-dom";

import { apiClient, isApiError } from "../apiClient.ts";
import MainSkeleton from "../components/MainSkeleton.tsx";
import type { BasicTaskResponse } from "../schemas/general.ts";
import type {
  BucketEntry,
  ModuleBucketResponse,
} from "../schemas/module_bucket.ts";
import { parseBucketData, type ParsedBlock } from "../services/bucket.ts";
import { useErrorStore } from "../stores/errorStore.ts";
import { useNotificationStore } from "../stores/notificationStore.ts";
import { snakeCaseToTitle } from "../utils.ts";

export function BucketPage() {
  const navigate = useNavigate();
  const module = useParams<{ module: string }>();
  const { addError } = useErrorStore();
  const { markAsConsumed } = useNotificationStore();

  const [entries, setEntries] = useState<BucketEntry[]>([]);
  const [parsedEntries, setParsedEntries] = useState<
    Record<string, { lines: string[]; blocks: ParsedBlock[] } | null>
  >({});
  const [activeEntryId, setActiveEntryId] = useState<string | null>(null);

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

    setEntries([]);
    setParsedEntries({});
    setActiveEntryId(null);
    markAsConsumed(module.module);

    const getBucket = async () => {
      const response = await apiClient.get<ModuleBucketResponse>(
        `/module/bucket?module_name=${module.module}`,
      );

      if (isApiError(response)) {
        addError(
          `Failed to fetch bucket (${response.statusCode}): ${response.detail || response.message}`,
        );
        return;
      }

      const nextEntries = Array.isArray(response.entries)
        ? response.entries
        : [];
      setEntries(nextEntries);

      const parsed: Record<
        string,
        { lines: string[]; blocks: ParsedBlock[] } | null
      > = {};

      nextEntries.forEach((entry) => {
        if (!entry.data) {
          parsed[entry.uuid] = null;
          return;
        }

        try {
          const result = parseBucketData(entry.data);
          parsed[entry.uuid] = {
            lines: result.cleanText.split("\n"),
            blocks: result.blocks,
          };
        } catch (error) {
          const clientLabel = entry.client_username ?? "Unknown client";
          addError(
            `Failed to parse bucket data for ${clientLabel}: ${
              error instanceof Error ? error.message : "Unknown error"
            }`,
          );
          parsed[entry.uuid] = null;
        }
      });

      setParsedEntries(parsed);
      setActiveEntryId((prev) => {
        if (prev && nextEntries.some((entry) => entry.uuid === prev)) {
          return prev;
        }

        return nextEntries.length > 0 ? nextEntries[0].uuid : null;
      });
    };

    getBucket();
  }, [module, addError, markAsConsumed]);

  const renderBlock = (block: ParsedBlock) => {
    switch (block.type.toLowerCase()) {
      case "image":
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

  const renderParsedContent = (entry: BucketEntry) => {
    const parsed = parsedEntries[entry.uuid];
    if (!parsed) {
      return (
        <div className="whitespace-pre-wrap">
          {entry.data || "No data for this client yet."}
        </div>
      );
    }

    const { lines, blocks } = parsed;
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

  const renderEntryContent = (entry: BucketEntry) => {
    const hasData = entry.data.trim().length > 0;

    return (
      <>
        {hasData ? (
          renderParsedContent(entry)
        ) : (
          <div className="text-sm text-gray-500">Awaiting bucket data.</div>
        )}
      </>
    );
  };

  const activeEntry = useMemo(
    () => entries.find((entry) => entry.uuid === activeEntryId) ?? null,
    [entries, activeEntryId],
  );

  return (
    <MainSkeleton
      baseName={
        module?.module ? "Bucket for " + snakeCaseToTitle(module.module) : "N/A"
      }
    >
      <div className="flex flex-col h-[77vh] bg-black rounded-lg overflow-hidden border border-gray-800">
        <div className="bg-gray-200 border-b dark:bg-gray-700 border-gray-300">
          {entries.length === 0 ? (
            <div className="px-4 py-3 text-sm text-gray-400">
              No clients have provided bucket data yet.
            </div>
          ) : (
            <div className="flex overflow-x-auto">
              {entries.map((entry) => {
                const isActive = entry.uuid === activeEntryId;
                const label = entry.client_username ?? "Unassigned client";

                return (
                  <button
                    key={entry.uuid}
                    type="button"
                    onClick={() => setActiveEntryId(entry.uuid)}
                    className={`px-4 py-2 text-sm border-b-2 transition-colors ${
                      isActive
                        ? "border-purple-500 text-black dark:text-white"
                        : "border-transparent text-gray-600 dark:text-gray-300 hover:text-gray-500 hover:border-gray-600"
                    }`}
                  >
                    {label}
                  </button>
                );
              })}
            </div>
          )}
        </div>

        <div className="flex-1 overflow-auto p-4 font-mono text-sm text-white bg-black">
          {activeEntry ? (
            renderEntryContent(activeEntry)
          ) : (
            <div className="text-sm text-gray-500">
              Select a client tab to view bucket data.
            </div>
          )}
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
