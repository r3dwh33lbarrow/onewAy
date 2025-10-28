export interface ParsedBlock {
  index: number;
  type: string;
  content: string;
}

export interface ParseResult {
  cleanText: string;
  blocks: ParsedBlock[];
}

const DATA_START = "[ONEWAY DATA START]";
const DATA_END = "[ONEWAY DATA END]";

export function parseBucketData(data: string): ParseResult {
  const lines = data.split(/\r?\n/);
  const blocks: ParsedBlock[] = [];
  const cleanLines: string[] = [];

  let inData = false;
  let dataType: string | null = null;
  let buffer: string[] = [];

  for (const rawLine of lines) {
    const line = rawLine.trim();

    if (line.startsWith(DATA_START)) {
      if (inData) {
        throw new Error("Nested data block found without closing previous one");
      }

      const match = line.match(/\[ONEWAY DATA START]\s*\[([^\]]+)\]/);
      if (!match) {
        throw new Error("Data block start missing type");
      }

      dataType = match[1];
      buffer = [];
      inData = true;
      continue;
    }

    if (line.startsWith(DATA_END)) {
      if (!inData) {
        throw new Error("Unexpected data end without start");
      }

      const match = line.match(/\[ONEWAY DATA END]\s*\[([^\]]+)]/);
      const endType = match?.[1];
      if (!endType || endType !== dataType) {
        throw new Error(
          `Data end type mismatch: expected ${dataType}, got ${endType || "unknown"}`,
        );
      }

      blocks.push({
        index: cleanLines.length,
        type: dataType!,
        content: buffer.join("\n").trim(),
      });

      inData = false;
      dataType = null;
      buffer = [];
      continue;
    }

    if (inData) {
      buffer.push(rawLine);
    } else {
      cleanLines.push(rawLine);
    }
  }

  if (inData) {
    throw new Error(`Unclosed data block of type ${dataType}`);
  }

  return {
    cleanText: cleanLines.join("\n").trim(),
    blocks,
  };

  return {
    cleanText: cleanLines.join("\n").trim(),
    blocks,
  };
}
