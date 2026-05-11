import tulipPreset from '@tulip/design-tokens/tailwind-preset';
import type { Config } from 'tailwindcss';

const config: Config = {
  presets: [tulipPreset as Config],
  content: [
    './src/**/*.{ts,tsx}',
    // workspace UI 패키지 소스도 스캔하여 Tailwind 클래스 추출
    '../../packages/ui/src/**/*.{ts,tsx}',
  ],
};

export default config;
