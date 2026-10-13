/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  async rewrites() {
    const backendUrl =
      process.env.BACKEND_URL ||
      process.env.API_URL ||
      process.env.NEXT_PUBLIC_API_URL;

    if (!backendUrl) {
      return [];
    }
    return [
      {
        source: "/universes/:path*",
        destination: `${backendUrl}/universes/:path*`,
      },
      {
        source: "/api/health",
        destination: `${backendUrl}/api/health`,
      },
    ];
  },
};

module.exports = nextConfig;
