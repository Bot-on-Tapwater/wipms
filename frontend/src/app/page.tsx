import { redirect } from "next/navigation";

// The dashboard sends people who are not logged in to /login.
export default function HomePage() {
  redirect("/dashboard");
}
