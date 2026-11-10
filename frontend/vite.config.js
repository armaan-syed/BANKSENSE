import path from "node:path";
import { fileURLToPath } from "node:url";

import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";

const repoRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");

const LOCAL_HOSTNAMES = new Set([
  "localhost",
  "localhost.localdomain",
  "ip6-localhost",
  "ip6-loopback",
  "0.0.0.0",
  "::",
  "::1",
]);

function isPrivateIpv4(hostname) {
  const parts = hostname.split(".");
  if (parts.length !== 4 || !parts.every((part) => /^\d{1,3}$/.test(part))) {
    return false;
  }
  const octets = parts.map(Number);
  if (octets.some((octet) => octet > 255)) {
    return true;
  }
  const [first, second] = octets;
  return (
    first === 0 ||
    first === 10 ||
    first === 127 ||
    (first === 169 && second === 254) ||
    (first === 172 && second >= 16 && second <= 31) ||
    (first === 192 && second === 168) ||
    (first === 100 && second >= 64 && second <= 127)
  );
}

function isPrivateHostname(hostname) {
  const host = hostname.toLowerCase().replace(/^\[|\]$/g, "");
  if (!host) {
    return true;
  }
  if (LOCAL_HOSTNAMES.has(host) || host.startsWith("127.")) {
    return true;
  }
  if (
    host.endsWith(".localhost") ||
    host.endsWith(".local") ||
    host.endsWith(".internal") ||
    host.endsWith(".home.arpa") ||
    host === "metadata.google.internal"
  ) {
    return true;
  }
  if (host.includes(":")) {
    if (host.startsWith("::ffff:")) {
      return isPrivateIpv4(host.slice("::ffff:".length));
    }
    return (
      host === "::1" ||
      host === "::" ||
      host.startsWith("fe80:") ||
      host.startsWith("fc") ||
      host.startsWith("fd")
    );
  }
  return isPrivateIpv4(host);
}

function assertProductionApiBaseUrl(value) {
  if (!value) {
    throw new Error(
      "VITE_API_BASE_URL is required for Vercel builds. Set it to the " +
        "Fly.io backend origin, for example https://banksense-api.fly.dev.",
    );
  }

  let parsed;
  try {
    parsed = new URL(value);
  } catch {
    throw new Error(
      `VITE_API_BASE_URL must be a valid absolute URL. Received "${value}".`,
    );
  }

  if (parsed.protocol !== "https:") {
    throw new Error(
      "VITE_API_BASE_URL must use https:// for Vercel builds. " +
        "http:// is only allowed for the local Vite dev proxy.",
    );
  }
  if (parsed.username || parsed.password) {
    throw new Error("VITE_API_BASE_URL must not contain credentials.");
  }
  if (parsed.pathname !== "/" || parsed.search || parsed.hash) {
    throw new Error(
      "VITE_API_BASE_URL must be a backend origin only (no path, query, or " +
        `hash). Received "${value}".`,
    );
  }
  if (isPrivateHostname(parsed.hostname)) {
    throw new Error(
      "VITE_API_BASE_URL must point to a public backend host, not localhost, " +
        `a loopback address, or a private network. Received "${value}".`,
    );
  }
}

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, repoRoot, "");
  const supabaseUrl = env.VITE_SUPABASE_URL || env.SUPABASE_URL || "";
  const publishableKey =
    env.VITE_SUPABASE_PUBLISHABLE_KEY || env.SUPABASE_PUBLISHABLE_KEY || "";
  const apiBaseUrl = (env.VITE_API_BASE_URL || "").trim().replace(/\/+$/, "");

  // The frontend and backend are separate origins in production (Vercel +
  // Fly.io). Fail the Vercel build instead of shipping a bundle that would
  // call the frontend host, localhost, or a private address.
  if (process.env.VERCEL) {
    assertProductionApiBaseUrl(apiBaseUrl);
  }

  return {
    plugins: [react()],
    envDir: repoRoot,
    define: {
      "import.meta.env.VITE_SUPABASE_URL": JSON.stringify(supabaseUrl),
      "import.meta.env.VITE_SUPABASE_PUBLISHABLE_KEY":
        JSON.stringify(publishableKey),
      "import.meta.env.VITE_API_BASE_URL": JSON.stringify(apiBaseUrl),
    },
    server: {
      port: 5173,
      proxy: {
        "/api": {
          target: "http://127.0.0.1:8000",
          changeOrigin: true,
        },
      },
    },
  };
});
