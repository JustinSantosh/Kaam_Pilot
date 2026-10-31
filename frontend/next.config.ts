import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "standalone", // small self-contained server for the Docker image (Phase 13)
};

export default nextConfig;
