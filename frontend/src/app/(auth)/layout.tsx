import Link from "next/link";
import { Logo } from "@/components/game/logo";

export default function AuthLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="app-backdrop flex min-h-dvh flex-col">
      <header className="px-6 py-5">
        <Link href="/" aria-label="StudyRaid home">
          <Logo />
        </Link>
      </header>
      <main className="flex flex-1 items-center justify-center px-4 pb-16">{children}</main>
    </div>
  );
}
