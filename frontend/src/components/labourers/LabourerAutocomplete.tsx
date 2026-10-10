"use client";

// A text input that suggests labourers already registered in the system
// while you type a name or national ID number (GET /labourers/search).
// Picking a suggestion calls onPick so the form can reuse that labourer
// instead of registering the same person twice.

import { useEffect, useId, useState } from "react";
import { Field, controlClass } from "@/components/ui/Form";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { choiceLabel } from "@/lib/format";
import type { LabourerSuggestion } from "@/lib/types";
import { useChoices } from "@/lib/useChoices";

const MIN_LENGTH = 2; // the backend needs at least 2 characters
const WAIT_MS = 250; // wait for the user to stop typing before searching

interface LabourerAutocompleteProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label: string;
  hint?: string;
  value: string;
  onPick: (labourer: LabourerSuggestion) => void;
}

/** Name or ID number input with a dropdown of matching labourers. */
export function LabourerAutocomplete({ label, hint, value, onPick, ...rest }: LabourerAutocompleteProps) {
  const { can } = useAuth();
  const { labourer_titles } = useChoices();
  const id = useId();
  const [open, setOpen] = useState(false);
  const [highlighted, setHighlighted] = useState(0);
  // Results are stored with the text they were searched for, so old
  // results are never shown for new text.
  const [results, setResults] = useState<{ query: string; items: LabourerSuggestion[] }>({
    query: "",
    items: [],
  });

  const query = value.trim();
  const enabled = can("labourers.view") && query.length >= MIN_LENGTH;

  useEffect(() => {
    if (!enabled) {
      return;
    }
    let active = true;
    const timer = setTimeout(() => {
      api
        .get<LabourerSuggestion[]>("/labourers/search", { q: query, limit: 8 })
        .then((items) => active && setResults({ query, items }))
        .catch(() => active && setResults({ query, items: [] })); // suggestions are only a helper
    }, WAIT_MS);
    return () => {
      active = false;
      clearTimeout(timer);
    };
  }, [enabled, query]);

  const suggestions = enabled && open && results.query === query ? results.items : [];

  /** Close the list and pass the chosen labourer to the form. */
  function handleSelect(labourer: LabourerSuggestion) {
    setOpen(false);
    onPick(labourer);
  }

  /** Arrow keys move through the list, Enter picks a labourer and Escape closes the list. */
  function handleKeyDown(event: React.KeyboardEvent<HTMLInputElement>) {
    if (suggestions.length === 0) {
      return;
    }
    if (event.key === "ArrowDown") {
      event.preventDefault();
      setHighlighted((current) => (current + 1) % suggestions.length);
    } else if (event.key === "ArrowUp") {
      event.preventDefault();
      setHighlighted((current) => (current - 1 + suggestions.length) % suggestions.length);
    } else if (event.key === "Enter") {
      event.preventDefault();
      handleSelect(suggestions[Math.min(highlighted, suggestions.length - 1)]);
    } else if (event.key === "Escape") {
      event.preventDefault(); // only close the list, not a modal around it
      setOpen(false);
    }
  }

  return (
    <Field label={label} htmlFor={id} hint={hint}>
      <div className="relative">
        <input
          id={id}
          className={controlClass}
          autoComplete="off"
          role="combobox"
          aria-expanded={suggestions.length > 0}
          aria-controls={`${id}-list`}
          value={value}
          onFocus={() => setOpen(true)}
          onBlur={() => setOpen(false)}
          onKeyDown={handleKeyDown}
          onInput={() => {
            setOpen(true);
            setHighlighted(0);
          }}
          {...rest}
        />
        {suggestions.length > 0 && (
          <ul
            id={`${id}-list`}
            role="listbox"
            className="absolute z-20 mt-1 max-h-64 w-full overflow-y-auto rounded-lg border border-zinc-200 bg-white py-1 shadow-lg"
          >
            {suggestions.map((labourer, index) => (
              <li
                key={labourer.id}
                role="option"
                aria-selected={index === highlighted}
                // mousedown (not click) so it runs before the input loses focus
                onMouseDown={(event) => {
                  event.preventDefault();
                  handleSelect(labourer);
                }}
                onMouseEnter={() => setHighlighted(index)}
                className={`cursor-pointer px-3 py-2 ${index === highlighted ? "bg-emerald-50" : ""}`}
              >
                <p className="text-sm font-medium text-zinc-900">{labourer.name}</p>
                <p className="text-xs text-zinc-500">
                  ID {labourer.national_id_number} · {choiceLabel(labourer_titles, labourer.title)} · {labourer.phone_number}
                </p>
              </li>
            ))}
          </ul>
        )}
      </div>
    </Field>
  );
}
