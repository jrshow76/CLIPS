/** @type {import('next').NextConfig} */
const apiBase = process.env.NEXT_PUBLIC_API_BASE_URL ?? 'http://localhost:8000';

const nextConfig = {
  reactStrictMode: true,
  poweredByHeader: false,
  output: 'standalone',
  experimental: {
    typedRoutes: false,
  },
  async rewrites() {
    // 동일 출처(same-origin)로 API 호출 시 백엔드로 프록시.
    // 직접 NEXT_PUBLIC_API_BASE_URL을 클라이언트에서 사용한다면 이 rewrites는 보조 역할.
    return [
      {
        source: '/api/v1/:path*',
        destination: `${apiBase}/api/v1/:path*`,
      },
      {
        source: '/ws/:path*',
        destination: `${apiBase}/ws/:path*`,
      },
    ];
  },
};

export default nextConfig;
