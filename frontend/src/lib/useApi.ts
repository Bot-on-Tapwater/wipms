"use client";

// Loads data from a GET endpoint for a page or component.
//
//   const { data, error, loading, reload } = useApi<Project[]>("/projects");
//
// Pass null as the path to skip loading (e.g. when the user lacks the
// permission). Call reload() after a change to fetch fresh data.

import { useCallback, useEffect, useState } from "react";
import { api, buildQuery, errorMessage, type QueryValue } from "./api";

/** Loads data from a GET endpoint and loads it again when the path or query changes. */
export function useApi<T>(path: string | null, query?: Record<string, QueryValue>) {
  const url = path === null ? null : path + buildQuery(query);
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loadedUrl, setLoadedUrl] = useState<string | null>(null);
  const [version, setVersion] = useState(0);

  useEffect(() => {
    if (url === null) {
      return;
    }
    let active = true;
    api
      .get<T>(url)
      .then((result) => {
        if (active) {
          setData(result);
          setError(null);
        }
      })
      .catch((reason) => {
        if (active) {
          setError(errorMessage(reason));
        }
      })
      .finally(() => {
        if (active) {
          setLoadedUrl(url);
        }
      });
    // Ignore the answer of a request that is no longer needed.
    return () => {
      active = false;
    };
  }, [url, version]);

  /** Fetch the data again. */
  const reload = useCallback(() => {
    setVersion((current) => current + 1);
  }, []);

  // Loading only until the first answer for this URL; reloads keep showing
  // the current data so the page does not flash.
  const loading = url !== null && loadedUrl !== url && data === null;

  return { data, error, loading, reload, setData };
}
