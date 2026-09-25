"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { LogoMark } from "@/components/game/logo";
import { MobileNav } from "@/components/shell/mobile-nav";
import { Sidebar } from "@/components/shell/sidebar";
import { Topbar } from "@/components/shell/topbar";
import { useAuth } from "@/lib/auth";
import { RealtimeProvider } from "@/lib/realtime";

export default function AppLayout({ children }: { children: React.ReactNode }) {
  const { status } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (status === "anonymous") router.replace(`/login?next=${encodeURIComponent(window.location.pathname)}`);
  }, [status, router]);

  if (status !== "authenticated") {
    return (
      <div className="flex min-h-dvh items-center justify-center" aria-busy="true">
        <div className="animate-pulse">
          <LogoMark size={40} />
        </div>
      </div>
    );
  }

  return (
    <RealtimeProvider enabled>
      <div className="app-backdrop flex min-h-dvh">
        <Sidebar />
        <div className="flex min-w-0 flex-1 flex-col">
          <Topbar />
          <main id="main" className="mx-auto w-full max-w-[1320px] flex-1 px-4 pt-6 pb-28 sm:px-6 lg:px-8 lg:pb-12">
            {children}
          </main>
        </div>
      </div>
      <MobileNav />
    </RealtimeProvider>
  );
}
