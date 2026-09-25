import { NextResponse, type NextRequest } from "next/server";

// A fast first check before any app page renders: no refresh cookie, no app.
// The client still verifies the session. This only avoids a flash of the
// dashboard for signed-out visitors.
export function proxy(request: NextRequest) {
  if (!request.cookies.has("sr_refresh")) {
    const url = new URL("/login", request.url);
    url.searchParams.set("next", request.nextUrl.pathname);
    return NextResponse.redirect(url);
  }
  return NextResponse.next();
}

export const config = {
  matcher: ["/dashboard/:path*", "/quests/:path*", "/focus/:path*", "/party/:path*", "/analytics/:path*", "/achievements/:path*", "/settings/:path*"],
};
