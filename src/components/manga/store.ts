import { create } from "zustand";
import { useRouter } from "next/navigation";
import { useCallback } from "react";

interface AppState {
  sidebarOpen: boolean;
  setSidebarOpen: (v: boolean) => void;
  searchQuery: string;
  setSearchQuery: (v: string) => void;
  theme: string;
  user: { id: string; name: string; username?: string; avatar?: string } | null;
  anilistToken: string | null;
  openAuthModal: (mode?: string) => void;
  openConnectListModal: () => void;
  openEditListModal: (data?: any) => void;
  addToLibrary: (id: string) => void;
  removeFromLibrary: (id: string) => void;
  library: { key: string }[];
  recordMediaProgress: (data: any, timeout?: number) => void;
}

export const useAppStore = create<AppState>((set, get) => ({
  sidebarOpen: false,
  setSidebarOpen: (sidebarOpen) => set({ sidebarOpen }),
  searchQuery: "",
  setSearchQuery: (searchQuery) => set({ searchQuery }),
  theme: "dark",
  user: null,
  anilistToken: null,
  openAuthModal: () => console.log("auth modal not implemented"),
  openConnectListModal: () => console.log("connect list modal not implemented"),
  openEditListModal: () => console.log("edit list modal not implemented"),
  addToLibrary: (id) => { try { const s = JSON.parse(localStorage.getItem("mangamaru:library") || "[]"); s.push(id); localStorage.setItem("mangamaru:library", JSON.stringify(s)); } catch {} },
  removeFromLibrary: (id) => { try { const s = JSON.parse(localStorage.getItem("mangamaru:library") || "[]"); localStorage.setItem("mangamaru:library", JSON.stringify(s.filter((x: string) => x !== id))); } catch {} },
  library: [],
  recordMediaProgress: (data) => { try { localStorage.setItem(`mangamaru:progress:${data.mediaId}`, JSON.stringify(data)); } catch {} },
}));

export function useNavigate() {
  const router = useRouter();
  return useCallback(({ page, id, chapterId }: { page: string; id: string; chapterId?: string }) => {
    if (page === "manga-detail") router.push(`/manga/${id}`);
    else if (page === "manga-read") router.push(`/read/${id}/${chapterId || "1"}`);
    else if (page === "anime") router.push(`/manga/${id}`);
  }, [router]);
}
