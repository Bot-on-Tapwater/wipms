import { Suspense } from "react";
import { ResetPasswordForm } from "@/components/auth/ResetPasswordForm";
import { Loading } from "@/components/ui/States";

// The emailed link looks like /reset-password?user_id=...&token=...
// The form reads those from the URL, which needs a Suspense boundary.
export default function ResetPasswordPage() {
  return (
    <Suspense fallback={<Loading />}>
      <ResetPasswordForm />
    </Suspense>
  );
}
