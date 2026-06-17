"use client";

import { createAuthClient } from "better-auth/react";
import { inferAdditionalFields, jwtClient } from "better-auth/client/plugins";

import type { auth } from "@/lib/auth";

export const authClient = createAuthClient({
  baseURL: process.env.NEXT_PUBLIC_BETTER_AUTH_URL ?? "http://localhost:3000",
  plugins: [inferAdditionalFields<typeof auth>(), jwtClient()],
});

export type AuthClientSession = typeof authClient.$Infer.Session;
