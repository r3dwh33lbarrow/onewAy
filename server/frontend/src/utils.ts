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

export function generatePassword(length: number): string {
  const chars =
    "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789!@#$%^&*()-_=+[]{}|;:,.<>?";
  let password = "";

  if (typeof window !== "undefined" && window.crypto?.getRandomValues) {
    const randomValues = new Uint32Array(length);
    window.crypto.getRandomValues(randomValues);

    for (let i = 0; i < length; i++) {
      password += chars[randomValues[i] % chars.length];
    }
  } else {
    for (let i = 0; i < length; i++) {
      const randomIndex = Math.floor(Math.random() * chars.length);
      password += chars[randomIndex];
    }
  }

  return password;
}

export function titleCaseToDashCase(str: string): string {
  return str.toLowerCase().replace(/ /g, "-");
}
