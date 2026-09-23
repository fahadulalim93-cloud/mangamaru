"use client";
import { useEffect, useRef, useState, useCallback } from "react";

export function useReveal<T extends HTMLElement = HTMLDivElement>() {
  const ref = useRef<T>(null);
  const [inView, setInView] = useState(false);
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            setInView(true);
            observer.unobserve(entry.target);
          }
        });
      },
      { threshold: 0.05, rootMargin: "0px 0px -30px 0px" }
    );
    observer.observe(el);
    return () => observer.disconnect();
  }, []);
  return { ref, inView };
}

export function useLazyLoad<T extends HTMLElement = HTMLDivElement>(onVisible: () => void, rootMargin = "400px") {
  const ref = useRef<T>(null);
  const fired = useRef(false);
  const cb = useCallback(onVisible, [onVisible]);
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting && !fired.current) {
            fired.current = true;
            cb();
            observer.unobserve(entry.target);
          }
        });
      },
      { rootMargin: `${rootMargin} 0px ${rootMargin} 0px` }
    );
    observer.observe(el);
    return () => observer.disconnect();
  }, [cb, rootMargin]);
  return ref;
}

export function useScrollPosition() {
  const [scrollY, setScrollY] = useState(0);
  useEffect(() => {
    const handler = () => setScrollY(window.scrollY);
    window.addEventListener("scroll", handler, { passive: true });
    return () => window.removeEventListener("scroll", handler);
  }, []);
  return scrollY;
}

export function useKeyboardShortcuts(handlers: Record<string, () => void>) {
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      const target = e.target as HTMLElement;
      if (target.tagName === "INPUT" || target.tagName === "TEXTAREA" || target.isContentEditable) return;
      const isMod = e.metaKey || e.ctrlKey;
      const key = e.key.toLowerCase();
      if (isMod && key === "k") { e.preventDefault(); handlers.search?.(); }
      else if (isMod && key === "b") { e.preventDefault(); handlers.toggleSidebar?.(); }
      else if (isMod && e.shiftKey && key === "b") { e.preventDefault(); handlers.bookmarks?.(); }
      else if (isMod && key === ",") { e.preventDefault(); handlers.settings?.(); }
      else if (key === "arrowright" && handlers.nextPage) { e.preventDefault(); handlers.nextPage(); }
      else if (key === "arrowleft" && handlers.prevPage) { e.preventDefault(); handlers.prevPage(); }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [handlers]);
}
