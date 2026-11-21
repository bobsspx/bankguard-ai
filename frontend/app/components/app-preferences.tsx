"use client";

import { useEffect, useState } from "react";

export function AppPreferences({ children }: { children: React.ReactNode }) {
  useEffect(() => {
    document.documentElement.dataset.theme = localStorage.getItem("bankguard-theme") === "light" ? "light" : "dark";
    document.documentElement.dataset.sidebar = localStorage.getItem("bankguard-sidebar") === "collapsed" ? "collapsed" : "expanded";
  }, []);
  return children;
}

export function useAppPreferences() {
  const [theme, setTheme] = useState<"dark" | "light">("dark");
  const [collapsed, setCollapsed] = useState(false);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      setTheme(localStorage.getItem("bankguard-theme") === "light" ? "light" : "dark");
      setCollapsed(localStorage.getItem("bankguard-sidebar") === "collapsed");
      setReady(true);
    }, 0);
    return () => window.clearTimeout(timer);
  }, []);

  useEffect(() => {
    if (!ready) return;
    document.documentElement.dataset.theme = theme;
    document.documentElement.dataset.sidebar = collapsed ? "collapsed" : "expanded";
    localStorage.setItem("bankguard-theme", theme);
    localStorage.setItem("bankguard-sidebar", collapsed ? "collapsed" : "expanded");
  }, [theme, collapsed, ready]);

  return {
    theme,
    toggleTheme: () => setTheme(current => current === "dark" ? "light" : "dark"),
    collapsed,
    toggleCollapsed: () => setCollapsed(current => !current),
  };
}
