"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";
import type { CurrentUser } from "@/lib/types";
import { visibleNavigation } from "@/lib/navigation";
import { useAppPreferences } from "./app-preferences";

export default function AppSidebar({ user, onLogout }: {
  user: CurrentUser | null;
  onLogout: () => void;
}) {
  const pathname = usePathname();
  const { theme, toggleTheme, collapsed, toggleCollapsed } = useAppPreferences();
  const [mobileOpen, setMobileOpen] = useState(false);

  return <aside className={`sidebar appSidebar${collapsed ? " isCollapsed" : ""}${mobileOpen ? " mobileOpen" : ""}`}>
    <div>
      <div className="appSidebarTop">
        <Link href="/" className="logoRow" aria-label="BankGuard home">
          <span className="brandMark">BG</span>
          <span className="appBrandText"><strong>BANKGUARD</strong><span>AI</span></span>
        </Link>
        <button type="button" className="appMobileToggle" aria-label="Toggle navigation"
          aria-expanded={mobileOpen} aria-controls="app-navigation"
          onClick={() => setMobileOpen(open => !open)}>{mobileOpen ? "Close" : "Menu"}</button>
        <button type="button" className="appCollapseToggle" aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
          title={collapsed ? "Expand sidebar" : "Collapse sidebar"} aria-expanded={!collapsed}
          onClick={toggleCollapsed}>{collapsed ? "›" : "‹"}</button>
      </div>
      <nav id="app-navigation" aria-label="Main navigation">
        {visibleNavigation(user?.permissions ?? []).map(item => {
          const active = item.href === "/" ? pathname === "/" : pathname.startsWith(item.href);
          return <Link key={item.href} href={item.href} aria-label={item.label}
            aria-current={active ? "page" : undefined} title={item.label}
            className={active ? "active" : undefined} onClick={() => setMobileOpen(false)}>
            <span className="appNavIcon" aria-hidden="true">{item.icon}</span>
            <span className="appNavLabel">{item.label}</span>
          </Link>;
        })}
      </nav>
    </div>
    <div className="appSidebarBottom">
      <button type="button" className="appThemeToggle" onClick={toggleTheme}
        aria-label={`Switch to ${theme === "dark" ? "light" : "dark"} theme`}
        title={`Switch to ${theme === "dark" ? "light" : "dark"} theme`}>
        <span className="appNavIcon" aria-hidden="true">{theme === "dark" ? "☼" : "☾"}</span>
        <span className="appNavLabel">{theme === "dark" ? "Light theme" : "Dark theme"}</span>
      </button>
      <button type="button" className="signOut" onClick={onLogout} title="Sign out" aria-label="Sign out">
        <span className="appNavIcon" aria-hidden="true">↪</span>
        <span className="appNavLabel">Sign out</span>
      </button>
    </div>
  </aside>;
}
