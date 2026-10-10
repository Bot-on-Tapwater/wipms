"use client";

// A button that calls the API, shows a toast with the result and, when
// `confirm` is set, asks "are you sure?" first. Used for one-click actions
// such as approving, deleting or paying out.
//
//   <ActionButton
//     action={() => api.post(`/works/${id}/payment-request`)}
//     success="Payment requested"
//     onDone={reload}
//   >
//     Request payment
//   </ActionButton>

import { useState } from "react";
import { notify, type SuccessMessage } from "@/lib/notify";
import { Button, type ButtonProps } from "./Button";
import { Modal } from "./Modal";

interface ActionButtonProps<T> extends Omit<ButtonProps, "onClick" | "loading"> {
  action: () => Promise<T>;
  success: SuccessMessage<T>;
  onDone?: (result: T) => void;
  confirm?: string;
  confirmLabel?: string;
}

/** Calls the API when clicked, after an optional "are you sure?" dialog. */
export function ActionButton<T>({
  action,
  success,
  onDone,
  confirm,
  confirmLabel = "Yes, continue",
  variant,
  children,
  ...rest
}: ActionButtonProps<T>) {
  const [busy, setBusy] = useState(false);
  const [asking, setAsking] = useState(false);

  /** Run the action, show the toast and pass the result to onDone. */
  async function handleAction() {
    setBusy(true);
    const result = await notify(action(), success);
    setBusy(false);
    setAsking(false);
    if (result !== null && onDone) {
      onDone(result);
    }
  }

  return (
    <>
      <Button
        variant={variant}
        loading={busy && !asking}
        onClick={() => (confirm ? setAsking(true) : handleAction())}
        {...rest}
      >
        {children}
      </Button>
      {confirm && (
        <Modal open={asking} title="Please confirm" onClose={() => !busy && setAsking(false)}>
          <p className="text-sm text-zinc-600">{confirm}</p>
          <div className="mt-5 flex justify-end gap-2">
            <Button variant="secondary" onClick={() => setAsking(false)} disabled={busy}>
              Cancel
            </Button>
            <Button variant={variant === "danger" ? "danger" : "primary"} loading={busy} onClick={handleAction}>
              {confirmLabel}
            </Button>
          </div>
        </Modal>
      )}
    </>
  );
}
