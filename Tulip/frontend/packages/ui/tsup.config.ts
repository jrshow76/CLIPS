import { promises as fs } from 'node:fs';
import path from 'node:path';
import { defineConfig } from 'tsup';

/**
 * @tulip/ui 빌드 설정
 *
 * - 본 라이브러리의 모든 컴포넌트는 인터랙티브한 것이 다수이므로
 *   번들 최상단에 `'use client'` 디렉티브를 강제로 삽입한다.
 * - Next.js App Router의 서버 컴포넌트에서도 import 가능하며,
 *   해당 컴포넌트는 자동으로 클라이언트 경계로 처리된다.
 * - 순수 디스플레이 컴포넌트(Badge, Label 등)도 함께 클라이언트로 묶이는
 *   트레이드오프는 Phase 1-B에서 컴포넌트별 분할 export로 개선한다.
 */
export default defineConfig({
  entry: ['src/index.ts'],
  format: ['esm', 'cjs'],
  dts: true,
  clean: true,
  external: ['react', 'react-dom'],
  treeshake: true,
  sourcemap: false,
  // 번들 최상단에 'use client' 디렉티브를 prepend.
  // esbuild banner는 디렉티브 형태로 인식해 ignore 되므로 post-build에서 직접 prepend.
  async onSuccess() {
    const distDir = path.resolve(__dirname, 'dist');
    for (const file of ['index.mjs', 'index.js']) {
      const filepath = path.join(distDir, file);
      const content = await fs.readFile(filepath, 'utf8');
      if (!content.startsWith("'use client'")) {
        await fs.writeFile(filepath, `'use client';\n${content}`, 'utf8');
      }
    }
  },
});
