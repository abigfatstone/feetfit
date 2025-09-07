import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // 允许外部访问和局域网访问
  serverExternalPackages: [],
  // 允许所有地址的跨域访问
  allowedDevOrigins: ['*'],
  // 配置允许的主机
  async headers() {
    return [
      {
        source: '/(.*)',
        headers: [
          {
            key: 'Access-Control-Allow-Origin',
            value: '*',
          },
          {
            key: 'Access-Control-Allow-Methods',
            value: 'GET, POST, PUT, DELETE, OPTIONS',
          },
          {
            key: 'Access-Control-Allow-Headers',
            value: 'Content-Type, Authorization',
          },
        ],
      },
    ];
  },
};

export default nextConfig;
