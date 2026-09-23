"use client";
import { useState, useEffect } from "react";
import { usePathname } from "next/navigation";
import { Sidebar } from "@/components/layout/Sidebar";

interface AppShellProps {
  children: React.ReactNode;
}

export function AppShell({ children }: AppShellProps) {
  const [collapsed, setCollapsed] = useState(false);
  const pathname = usePathname();

  // Load saved sidebar state
  useEffect(() => {
    try {
      const saved = localStorage.getItem("mangamaru:sidebar-collapsed");
      if (saved !== null) setCollapsed(saved === "true");
    } catch {}
  }, []);

  // Save on change
  useEffect(() => {
    try {
      localStorage.setItem("mangamaru:sidebar-collapsed", String(collapsed));
    } catch {}
  }, [collapsed]);

  // Keyboard shortcut: ⌘B / Ctrl+B to toggle sidebar
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      const target = e.target as HTMLElement;
      if (target.tagName === "INPUT" || target.tagName === "TEXTAREA") return;
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "b" && !e.shiftKey) {
        e.preventDefault();
        setCollapsed((c) => !c);
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, []);

  return (
    <div className="app">
      <Sidebar collapsed={collapsed} onToggle={() => setCollapsed((c) => !c)} />
      <main className={`main ${collapsed ? "main-collapsed" : ""}`}>{children}</main>
    </div>
  );
}
