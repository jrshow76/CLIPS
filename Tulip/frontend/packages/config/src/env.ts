/**
 * 환경변수 검증 스키마 (zod)
 * Next.js 앱에서 `parseEnv(process.env)` 형태로 호출.
 */
import { z } from 'zod';

export const publicEnvSchema = z.object({
  NEXT_PUBLIC_APP_NAME: z.string().default('Tulip+'),
  NEXT_PUBLIC_APP_ENV: z.enum(['development', 'staging', 'production']).default('development'),
  NEXT_PUBLIC_API_BASE_URL: z.string().url().default('http://localhost:8080/api/v1'),
  NEXT_PUBLIC_AUTH_ISSUER: z.string().url().default('http://localhost:8081/realms/tulip'),
  NEXT_PUBLIC_AUTH_CLIENT_ID: z.string().default('tulip-admin'),
  NEXT_PUBLIC_DEFAULT_TENANT_ID: z.string().optional(),
  NEXT_PUBLIC_DEFAULT_LOCALE: z.enum(['ko-KR', 'en-US']).default('ko-KR'),
});

export type PublicEnv = z.infer<typeof publicEnvSchema>;

export function parsePublicEnv(env: Record<string, string | undefined>): PublicEnv {
  const parsed = publicEnvSchema.safeParse(env);
  if (!parsed.success) {
    // eslint-disable-next-line no-console
    console.error('[@tulip/config] 환경변수 검증 실패', parsed.error.flatten().fieldErrors);
    throw new Error('환경변수 검증 실패. .env 파일을 확인하세요.');
  }
  return parsed.data;
}
