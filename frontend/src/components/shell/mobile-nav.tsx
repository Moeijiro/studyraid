"use client";

import clsx from "clsx";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { NAV } from "./nav";

/** Bottom tab bar on phones and tablets. Achievements live in the dashboard and the header menu there. */
export function MobileNav() {
  const path = usePathname();
  return (
    <nav aria-label="Main" className="fixed inset-x-0 bottom-0 z-40 border-t border-line bg-bg/90 pb-[env(safe-area-inset-bottom)] backdrop-blur-xl lg:hidden">
      <ul className="mx-auto grid max-w-lg grid-cols-5">
        {NAV.slice(0, 5).map(({ href, label, icon: Icon }) => {
          const active = path === href || path.startsWith(`${href}/`);
          return (
            <li key={href}>
              <Link href={href} aria-current={active ? "page" : undefined} className={clsx("flex h-16 flex-col items-center justify-center gap-1 text-[11px] font-medium", active ? "text-fg" : "text-faint")}>
                <Icon className={clsx("size-5", active && "text-brand")} />
                {label}
              </Link>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}
