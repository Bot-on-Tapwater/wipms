import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Builds a small self-contained server in .next/standalone (used by Dockerfile.prod).
  output: "standalone",
  turbopack: {
    rules: {
      "*.css": {
        loaders: ["@tailwindcss/turbopack"],
        as: "*.css",
      },
    },
  },
};

export default nextConfig;
