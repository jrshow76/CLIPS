import tulipPreset from '@tulip/design-tokens/tailwind-preset';
import type { Config } from 'tailwindcss';

const config: Config = {
  presets: [tulipPreset as Config],
  content: [
    './src/**/*.{ts,tsx}',
    '../../packages/ui/src/**/*.{ts,tsx}',
  ],
};

export default config;
