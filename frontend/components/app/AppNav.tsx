"use client";

import { Menu, X } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";

import { AvatarBadge } from "@/components/app/AvatarBadge";
import { Logo } from "@/components/brand/Logo";
import { useOnboarding } from "@/hooks/useOnboarding";
import { displayNameOrFallback } from "@/lib/personalization";

const links = [
  { href: "/home", label: "Home" },
  { href: "/matches", label: "Matches" },
  { href: "/profile", label: "My Profile" },
];

export function AppNav() {
  const pathname = usePathname();
  const { state } = useOnboarding();
  const [open, setOpen] = useState(false);
  const name = displayNameOrFallback(state.displayName);

  useEffect(() => {
    setOpen(false);
  }, [pathname]);

  return (
    <header className="sticky top-0 z-40 border-b border-white/10 bg-[#07080d]/90 backdrop-blur">
      <div className="mx-auto flex max-w-6xl items-center justify-between gap-4 px-5 py-3 md:px-8">
        <Link href="/home" aria-label="PulseIQ home">
          <Logo />
        </Link>
        <nav className="hidden items-center gap-7 text-sm font-medium text-white/70 md:flex">
          {links.map((link) => {
            const active =
              pathname === link.href || pathname.startsWith(`${link.href}/`);
            return (
              <Link
                key={link.href}
                href={link.href}
                aria-current={active ? "page" : undefined}
                className={`hover:text-white ${active ? "text-white" : ""}`}
              >
                {link.label}
              </Link>
            );
          })}
        </nav>
        <div className="flex items-center gap-3">
          <Link
            href="/profile"
            className="hidden items-center gap-2 rounded-full border border-white/10 bg-white/5 py-1 pr-3 pl-1 text-sm text-white/80 hover:text-white md:inline-flex"
          >
            <AvatarBadge name={name} avatarId={state.avatar} />
            <span className="max-w-[9rem] truncate">{name}</span>
          </Link>
          <button
            type="button"
            className="grid h-11 w-11 place-items-center rounded-full border border-white/15 bg-white/5 md:hidden"
            aria-expanded={open}
            aria-label={open ? "Close menu" : "Open menu"}
            onClick={() => setOpen((value) => !value)}
          >
            {open ? <X size={18} /> : <Menu size={18} />}
          </button>
        </div>
      </div>
      {open ? (
        <nav className="space-y-1 px-5 pb-4 md:hidden">
          {links.map((link) => (
            <Link
              key={link.href}
              href={link.href}
              className="block rounded-2xl px-4 py-3 text-white/90 hover:bg-white/5"
            >
              {link.label}
            </Link>
          ))}
        </nav>
      ) : null}
    </header>
  );
}
