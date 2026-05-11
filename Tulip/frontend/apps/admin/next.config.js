/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  poweredByHeader: false,
  // 모노레포 외부 패키지 트랜스파일 (workspace 패키지)
  transpilePackages: [
    '@tulip/ui',
    '@tulip/design-tokens',
    '@tulip/api-client',
    '@tulip/auth',
    '@tulip/config',
  ],
};

module.exports = nextConfig;
