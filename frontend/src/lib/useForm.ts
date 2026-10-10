"use client";

// Keeps the values of a form in one object.
//
//   const form = useForm({ name: "", location: "" });
//   <Input label="Name" {...form.field("name")} />
//   api.post("/projects", form.values);

import { useState } from "react";

type ChangeEvent = React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>;

/** Form values in one object, with field() props for each input and reset(). */
export function useForm<T extends Record<string, string>>(initial: T) {
  const [values, setValues] = useState<T>(initial);

  /** value + onChange props for an input, select or textarea. */
  function field(name: keyof T) {
    return {
      value: values[name],
      onChange: (event: ChangeEvent) => {
        const value = event.target.value;
        setValues((current) => ({ ...current, [name]: value }));
      },
    };
  }

  /** Put every field back to its starting value. */
  function reset() {
    setValues(initial);
  }

  return { values, setValues, field, reset };
}
