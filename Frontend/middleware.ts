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

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;

  if (isPublicPath(pathname)) {
    return NextResponse.next();
  }

  if (!isProtectedPath(pathname)) {
    return NextResponse.next();
  }

  if (hasBetterAuthSession(request)) {
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

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico|robots.txt|sitemap.xml).*)"],
};
