/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  poweredByHeader: false,
  transpilePackages: [
    '@tulip/ui',
    '@tulip/design-tokens',
    '@tulip/api-client',
    '@tulip/auth',
    '@tulip/config',
  ],
};

module.exports = nextConfig;
