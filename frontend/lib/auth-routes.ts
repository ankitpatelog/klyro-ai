export const apiUrl = (process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000").replace(/\/$/, "");

export function getSafeNextPath(value: string | null, fallback = "/dashboard") {
  if (!value || !value.startsWith("/") || value.startsWith("//")) {
    return fallback;
  }

  return value;
}

export function loginPath(nextPath: string) {
  return `/login?next=${encodeURIComponent(nextPath)}`;
}
