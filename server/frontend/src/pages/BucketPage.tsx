import { Button } from "flowbite-react";
import {
  type JSX,
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import { HiOutlineTrash } from "react-icons/hi";
import { useParams, useSearchParams } from "react-router-dom";

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
  const module = useParams<{ module: string }>();
  const [searchParams, setSearchParams] = useSearchParams();
  const { addError } = useErrorStore();
  const { markAsConsumed, query: refreshNotifications } =
    useNotificationStore();

  const [entries, setEntries] = useState<BucketEntry[]>([]);
  const [parsedEntries, setParsedEntries] = useState<
    Record<string, { lines: string[]; blocks: ParsedBlock[] } | null>
  >({});
  const requestedEntryId = searchParams.get("entry");
  const requestedEntryIdRef = useRef<string | null>(requestedEntryId);
  const [activeEntryId, setActiveEntryId] = useState<string | null>(
    requestedEntryId,
  );

  useEffect(() => {
    requestedEntryIdRef.current = requestedEntryId;
  }, [requestedEntryId]);

  const setActiveEntry = useCallback(
    (entryId: string | null, options?: { updateUrl?: boolean }) => {
      setActiveEntryId(entryId);
      if (options?.updateUrl === false) return;

      if (entryId) {
        setSearchParams({ entry: entryId }, { replace: true });
        return;
      }

      setSearchParams({}, { replace: true });
    },
    [setSearchParams],
  );

  const deleteBucketEntry = async () => {
    if (!module.module || !activeEntryId) return;

    const response = await apiClient.delete<BasicTaskResponse>(
      `/module/bucket-entry?module_name=${encodeURIComponent(module.module)}&entry_uuid=${activeEntryId}`,
    );
    if (isApiError(response)) {
      addError(
        `Failed to delete bucket entry (${response.statusCode}): ${response.detail || response.message}`,
      );
      return;
    }

    const remainingEntries = entries.filter(
      (entry) => entry.uuid !== activeEntryId,
    );

    setEntries(remainingEntries);
    setParsedEntries((prev) => {
      const next = { ...prev };
      delete next[activeEntryId];
      return next;
    });

    const currentIndex = entries.findIndex(
      (entry) => entry.uuid === activeEntryId,
    );
    let nextActive: string | null = null;

    if (remainingEntries.length > 0) {
      if (currentIndex >= 0 && currentIndex < remainingEntries.length) {
        nextActive = remainingEntries[currentIndex].uuid;
      } else {
        nextActive = remainingEntries[remainingEntries.length - 1].uuid;
      }
    }

    setActiveEntry(nextActive);
    await refreshNotifications({ force: true });
  };

  useEffect(() => {
    if (!module.module) return;

    setEntries([]);
    setParsedEntries({});
    setActiveEntry(requestedEntryIdRef.current, { updateUrl: false });
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
      const targetEntryId =
        requestedEntryIdRef.current &&
        nextEntries.some((entry) => entry.uuid === requestedEntryIdRef.current)
          ? requestedEntryIdRef.current
          : nextEntries.length > 0
            ? nextEntries[0].uuid
            : null;

      setActiveEntry(
        targetEntryId,
        targetEntryId === requestedEntryIdRef.current
          ? { updateUrl: false }
          : undefined,
      );
    };

    getBucket();
  }, [module, addError, markAsConsumed, setActiveEntry]);

  useEffect(() => {
    if (!entries.length) {
      return;
    }

    if (requestedEntryId) {
      const hasRequested = entries.some(
        (entry) => entry.uuid === requestedEntryId,
      );
      if (!hasRequested || activeEntryId === requestedEntryId) {
        return;
      }
      setActiveEntry(requestedEntryId, { updateUrl: false });
      return;
    }

    if (
      activeEntryId &&
      entries.some((entry) => entry.uuid === activeEntryId)
    ) {
      return;
    }

    const fallbackEntryId =
      entries.length > 0 ? entries[0].uuid : (activeEntryId ?? null);
    if (fallbackEntryId !== activeEntryId) {
      setActiveEntry(fallbackEntryId);
    }
  }, [requestedEntryId, entries, activeEntryId, setActiveEntry]);

  const handleEntryClick = useCallback(
    (entryId: string) => {
      if (entryId === activeEntryId) return;
      setActiveEntry(entryId);
    },
    [activeEntryId, setActiveEntry],
  );

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
                    onClick={() => handleEntryClick(entry.uuid)}
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
          onClick={deleteBucketEntry}
          disabled={!activeEntry}
        >
          <HiOutlineTrash className="h-5 w-5" />
          Delete Tab
        </Button>
      </div>
    </MainSkeleton>
  );
}
