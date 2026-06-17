"use client";

import { create } from "zustand";
import { persist } from "zustand/middleware";

import type { DoxaUser } from "@/lib/auth-types";

interface AuthState {
  accessToken: string | null;
  user: DoxaUser | null;
  setAccessToken: (token: string) => void;
  setUser: (user: DoxaUser | null) => void;
  clearAuth: () => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      accessToken: null,
      user: null,
      setAccessToken: (token) => set({ accessToken: token }),
      setUser: (user) => set({ user }),
      clearAuth: () => set({ accessToken: null, user: null }),
    }),
    {
      name: "doxa-crm-auth",
      partialize: (state) => ({
        accessToken: state.accessToken,
        user: state.user,
      }),
    },
  ),
);
