// Backend API client. All requests go to EXPO_PUBLIC_BACKEND_URL + /api.
// A single in-memory token mirror lets us build authenticated file URLs
// synchronously (web <img> cannot send Authorization headers, so reads use
// a ?token= query param that the backend also accepts).
import { Platform } from "react-native";

import { storage } from "@/src/utils/storage";

const BASE = process.env.EXPO_PUBLIC_BACKEND_URL;
if (!BASE) {
  // Surfaced clearly in the app rather than failing silently.
  console.error("EXPO_PUBLIC_BACKEND_URL is not set");
}
export const API = `${BASE}/api`;
export const TOKEN_KEY = "tf_token";

let memToken: string | null = null;

export async function setToken(token: string | null) {
  memToken = token;
  if (token) await storage.secureSet(TOKEN_KEY, token);
  else await storage.secureRemove(TOKEN_KEY);
}

export async function loadToken(): Promise<string | null> {
  if (memToken) return memToken;
  memToken = await storage.secureGet(TOKEN_KEY, null as unknown as string);
  return memToken;
}

export function fileUrl(path?: string | null): string | undefined {
  if (!path) return undefined;
  const t = memToken ? `?token=${encodeURIComponent(memToken)}` : "";
  return `${API}/files/${path}${t}`;
}

async function request<T>(method: string, path: string, body?: unknown): Promise<T> {
  const token = await loadToken();
  const res = await fetch(`${API}${path}`, {
    method,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!res.ok) {
    let detail: any = `Request failed (${res.status})`;
    try {
      const j = await res.json();
      detail = j.detail ?? detail;
    } catch {}
    const err: any = new Error(typeof detail === "string" ? detail : "Request failed");
    err.status = res.status;
    err.detail = detail;
    throw err;
  }
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

export const api = {
  get: <T,>(p: string) => request<T>("GET", p),
  post: <T,>(p: string, b?: unknown) => request<T>("POST", p, b),
  patch: <T,>(p: string, b?: unknown) => request<T>("PATCH", p, b),
  del: <T,>(p: string) => request<T>("DELETE", p),
};

export async function uploadPhoto(path: string, uri: string, name = "photo.jpg"): Promise<{ path: string }> {
  const token = await loadToken();
  const form = new FormData();
  const type = name.endsWith("png") ? "image/png" : "image/jpeg";
  if (Platform.OS === "web") {
    const blob = await (await fetch(uri)).blob();
    form.append("file", blob, name);
  } else {
    form.append("file", { uri, name, type } as any);
  }
  const res = await fetch(`${API}${path}`, {
    method: "POST",
    headers: { ...(token ? { Authorization: `Bearer ${token}` } : {}) },
    body: form,
  });
  if (!res.ok) throw new Error(`Upload failed (${res.status})`);
  return res.json();
}
