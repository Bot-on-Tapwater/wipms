import { HardHat } from "lucide-react";

/** The Ijenga name with a hard hat icon. */
export function Logo() {
  return (
    <span className="inline-flex items-center gap-2 text-lg font-semibold tracking-tight text-zinc-900">
      <span className="flex size-8 items-center justify-center rounded-lg bg-emerald-600 text-white">
        <HardHat className="size-5" aria-hidden />
      </span>
      Ijenga
    </span>
  );
}
