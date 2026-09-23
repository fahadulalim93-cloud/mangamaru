import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  reactStrictMode: true,
  output: "standalone",
  images: {
    remotePatterns: [
      { protocol: "https", hostname: "s4.anilist.co" },
      { protocol: "https", hostname: "s2.anilist.co" },
      { protocol: "https", hostname: "media.anilist.co" },
      { protocol: "https", hostname: "cdn.anilist.co" },
      { protocol: "https", hostname: "placehold.co" },
      { protocol: "http", hostname: "192.151.150.146" },
    ],
  },
};

export default nextConfig;
