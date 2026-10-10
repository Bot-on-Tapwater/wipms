"use client";

import { Toaster } from "sonner";
import { AuthProvider } from "@/lib/auth";

/** Everything the whole app needs: the logged in user and toast messages. */
export function Providers({ children }: { children: React.ReactNode }) {
  return (
    <AuthProvider>
      {children}
      <Toaster position="top-right" richColors closeButton />
    </AuthProvider>
  );
}
