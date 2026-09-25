import { LogoMark } from "@/components/game/logo";
import { ButtonLink } from "@/components/ui/button";

export default function NotFound() {
  return (
    <main className="app-backdrop flex min-h-dvh flex-col items-center justify-center px-6 text-center">
      <LogoMark size={44} />
      <p className="font-display mt-6 text-5xl font-bold">404</p>
      <p className="mt-2 text-muted">This part of the map hasn&apos;t been explored.</p>
      <ButtonLink href="/dashboard" className="mt-8">
        Back to base
      </ButtonLink>
    </main>
  );
}
