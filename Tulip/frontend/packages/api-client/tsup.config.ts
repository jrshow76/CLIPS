import { promises as fs } from 'node:fs';
import path from 'node:path';
import { defineConfig } from 'tsup';

/**
 * @tulip/api-client 빌드 설정
 *
 * - hooks/context는 React 클라이언트 컴포넌트 환경에서 사용되므로
 *   번들 최상단에 `'use client'` 디렉티브를 강제로 삽입한다.
 * - 순수 타입/유틸도 함께 클라이언트로 묶이는 트레이드오프는 추후 분할 export로 해결.
 */
export default defineConfig({
  entry: ['src/index.ts'],
  format: ['esm', 'cjs'],
  dts: true,
  clean: true,
  external: ['react', 'react-dom', '@tanstack/react-query'],
  treeshake: true,
  sourcemap: false,
  async onSuccess() {
    const distDir = path.resolve(__dirname, 'dist');
    for (const file of ['index.mjs', 'index.js']) {
      const filepath = path.join(distDir, file);
      try {
        const content = await fs.readFile(filepath, 'utf8');
        if (!content.startsWith("'use client'")) {
          await fs.writeFile(filepath, `'use client';\n${content}`, 'utf8');
        }
      } catch {
        // 해당 포맷이 비활성화되어 있을 수 있음
      }
    }
  },
});
