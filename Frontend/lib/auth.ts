import { betterAuth } from "better-auth";
import { nextCookies } from "better-auth/next-js";
import { jwt } from "better-auth/plugins";
import { SignJWT, type JWTPayload } from "jose";
import { Pool } from "pg";

import { normalizeRole } from "@/lib/auth-types";

const fallbackDatabaseUrl = "postgresql://postgres:postgres@127.0.0.1:5432/postgres";
const fallbackSecret = "doxa-crm-local-development-secret";
const envValue = (key: string, fallback: string): string => {
  const value = process.env[key];
  return value && value.trim().length > 0 ? value : fallback;
};

const databaseUrl = envValue("DATABASE_URL", fallbackDatabaseUrl);
const betterAuthUrl = envValue("BETTER_AUTH_URL", "http://localhost:3000");
const backendAudience = envValue("NEXT_PUBLIC_API_URL", "http://localhost:8001");
const betterAuthSecret =
  envValue("BETTER_AUTH_SECRET", process.env.SECRET_KEY && process.env.SECRET_KEY.trim().length > 0 ? process.env.SECRET_KEY : fallbackSecret);

const jwtSecret = new TextEncoder().encode(betterAuthSecret);

function normalizePgConnectionString(connectionString: string): string {
  try {
    const url = new URL(connectionString.replace("postgresql+asyncpg://", "postgresql://"));
    url.searchParams.delete("ssl");
    url.searchParams.delete("sslmode");
    url.searchParams.delete("uselibpqcompat");
    return url.toString();
  } catch {
    return connectionString;
  }
}

function shouldUseSsl(connectionString: string): boolean {
  try {
    const url = new URL(connectionString.replace("postgresql+asyncpg://", "postgresql://"));
    return Boolean(url.hostname.endsWith(".supabase.co") || url.hostname.endsWith(".pooler.supabase.com"));
  } catch {
    return false;
  }
}

const database = new Pool({
  allowExitOnIdle: true,
  connectionString: normalizePgConnectionString(databaseUrl),
  ssl: shouldUseSsl(databaseUrl) ? { rejectUnauthorized: false } : undefined,
});

function stringField(source: object, key: string): string | undefined {
  const value = (source as Record<string, unknown>)[key];
  return typeof value === "string" && value.length > 0 ? value : undefined;
}

function fastApiPayload(user: object): JWTPayload {
  const id = stringField(user, "id") ?? "";
  const email = stringField(user, "email") ?? "";
  const fullName = stringField(user, "full_name") ?? stringField(user, "name") ?? email;
  const role = normalizeRole(stringField(user, "role"));

  return {
    sub: id,
    id,
    email,
    full_name: fullName,
    role,
  };
}

export const auth = betterAuth({
  appName: "Doxa CRM",
  baseURL: betterAuthUrl,
  secret: betterAuthSecret,
  database,
  emailAndPassword: {
    enabled: true,
    requireEmailVerification: false,
  },
  user: {
    additionalFields: {
      full_name: {
        type: "string",
        required: false,
        defaultValue: "",
      },
      role: {
        type: "string",
        required: false,
        defaultValue: "sales_rep",
        input: false,
      },
    },
  },
  plugins: [
    jwt({
      jwks: {
        remoteUrl: `${betterAuthUrl}/api/auth/jwks`,
        keyPairConfig: {
          alg: "EdDSA",
        },
      },
      jwt: {
        issuer: betterAuthUrl,
        audience: backendAudience,
        expirationTime: "1h",
        definePayload: ({ user }) => fastApiPayload(user),
        sign: async (payload: JWTPayload) =>
          new SignJWT(payload)
            .setProtectedHeader({ alg: "HS256", typ: "JWT" })
            .setIssuedAt()
            .setExpirationTime("1h")
            .sign(jwtSecret),
      },
    }),
    nextCookies(),
  ],
});

export type AuthSession = typeof auth.$Infer.Session;
