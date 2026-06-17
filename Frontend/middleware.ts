import { NextResponse, type NextRequest } from "next/server";

const protectedPrefixes = [
  "/dashboard",
  "/accounts",
  "/contacts",
  "/deals",
  "/pipeline",
  "/leads",
  "/campaigns",
  "/activities",
  "/tasks",
  "/reports",
  "/projects",
  "/settings",
  "/search",
  "/users",
] as const;

const publicPrefixes = ["/login", "/portal", "/api/auth"] as const;
const settingsRoles = new Set(["super_admin", "sales_manager"]);

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;

  if (isPublicPath(pathname)) {
    return NextResponse.next();
  }

  if (!isProtectedPath(pathname)) {
    return NextResponse.next();
  }

  if (hasBetterAuthSession(request)) {
    if (isSettingsPath(pathname) && !canAccessSettings(request)) {
      const dashboardUrl = request.nextUrl.clone();
      dashboardUrl.pathname = "/dashboard";
      dashboardUrl.searchParams.set("settings", "unauthorized");
      return NextResponse.redirect(dashboardUrl);
    }

    return NextResponse.next();
  }

  const loginUrl = request.nextUrl.clone();
  loginUrl.pathname = "/login";
  loginUrl.searchParams.set("callbackUrl", pathname);
  return NextResponse.redirect(loginUrl);
}

function isPublicPath(pathname: string): boolean {
  return publicPrefixes.some((prefix) => pathname === prefix || pathname.startsWith(`${prefix}/`));
}

function isProtectedPath(pathname: string): boolean {
  return protectedPrefixes.some((prefix) => pathname === prefix || pathname.startsWith(`${prefix}/`));
}

function hasBetterAuthSession(request: NextRequest): boolean {
  return request.cookies
    .getAll()
    .some((cookie) => cookie.name === "doxa_auth_token" || (cookie.name.includes("better-auth") && cookie.name.includes("session")));
}

function isSettingsPath(pathname: string): boolean {
  return pathname === "/settings" || pathname.startsWith("/settings/");
}

function canAccessSettings(request: NextRequest): boolean {
  const role = roleFromCookies(request);
  return role === null || settingsRoles.has(role);
}

function roleFromCookies(request: NextRequest): string | null {
  for (const cookie of request.cookies.getAll()) {
    const directRole = roleFromText(cookie.value);
    if (directRole) {
      return directRole;
    }

    const jwtRole = roleFromJwt(cookie.value);
    if (jwtRole) {
      return jwtRole;
    }
  }

  return null;
}

function roleFromText(value: string): string | null {
  try {
    const decoded = decodeURIComponent(value);
    const parsed = JSON.parse(decoded) as unknown;
    if (typeof parsed === "object" && parsed !== null && "role" in parsed) {
      const role = (parsed as { role?: unknown }).role;
      return typeof role === "string" ? role : null;
    }
  } catch {
    // Cookie is not a JSON role payload.
  }

  return settingsRoles.has(value) || value.endsWith("_rep") || value.endsWith("_manager") || value === "read_only" || value === "customer_success"
    ? value
    : null;
}

function roleFromJwt(value: string): string | null {
  const parts = value.split(".");
  if (parts.length < 2) {
    return null;
  }

  try {
    const base64 = parts[1].replace(/-/g, "+").replace(/_/g, "/");
    const padded = base64.padEnd(base64.length + ((4 - (base64.length % 4)) % 4), "=");
    const payload = JSON.parse(atob(padded)) as { role?: unknown };
    return typeof payload.role === "string" ? payload.role : null;
  } catch {
    return null;
  }
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico|robots.txt|sitemap.xml).*)"],
};
