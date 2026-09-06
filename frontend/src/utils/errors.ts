import { ApiError } from "../api/client";

export function readableError(error: unknown): string {
  if (error instanceof ApiError) return error.message;
  if (error instanceof Error) return error.message;
  return "The request could not be completed. Check the local API and try again.";
}
