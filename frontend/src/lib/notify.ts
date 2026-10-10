// Runs an API call and shows a toast with the result.
//
//   const project = await notify(api.post("/projects", values), "Project created");
//   if (project) { ... }   // null means it failed (the error toast is already shown)
//
// `success` may also be a function that builds the message from the result.

import { toast } from "sonner";
import { errorMessage } from "./api";

export type SuccessMessage<T> = string | ((result: T) => string);

/** Waits for the API call and shows a toast. Returns null when it failed. */
export async function notify<T>(action: Promise<T>, success: SuccessMessage<T>): Promise<T | null> {
  try {
    const result = await action;
    toast.success(typeof success === "function" ? success(result) : success);
    return result;
  } catch (error) {
    toast.error(errorMessage(error));
    return null;
  }
}
