import type { ApiError } from "./apiClient.ts";

export function snakeCaseToTitle(str: string): string {
  return str
    .split("_")
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase())
    .join(" ");
}

export function snakeCaseToDashCase(str: string): string {
  return str.toLowerCase().replace(/_/g, "-");
}

export function apiErrorToString(error: ApiError) {
  return `${error.statusCode}: ${error.detail || error.message}`;
}
