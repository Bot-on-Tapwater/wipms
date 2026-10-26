"use client";

// Dropdown options (labourer titles, genders, task categories, roles) from
// GET /metadata/choices. Loaded once and shared by every form.

import { useEffect, useState } from "react";
import { api } from "./api";
import type { Choices } from "./types";

let cached: Promise<Choices> | null = null;

/** Fetches the choices once; later calls reuse the same request. */
function loadChoices(): Promise<Choices> {
  if (!cached) {
    cached = api.get<Choices>("/metadata/choices").catch((error) => {
      cached = null; // try again next time
      throw error;
    });
  }
  return cached;
}

const EMPTY: Choices = { labourer_titles: [], genders: [], task_categories: [], roles: [] };

/** Dropdown options for forms; empty lists until they have loaded. */
export function useChoices(): Choices {
  const [choices, setChoices] = useState<Choices>(EMPTY);

  useEffect(() => {
    let active = true;
    loadChoices()
      .then((result) => {
        if (active) {
          setChoices(result);
        }
      })
      .catch(() => {
        // Forms still work with empty dropdowns; the API rejects bad values.
      });
    return () => {
      active = false;
    };
  }, []);

  return choices;
}
