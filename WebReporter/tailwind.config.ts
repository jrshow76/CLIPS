import type { Config } from 'tailwindcss';

const config: Config = {
  content: [
    './src/pages/**/*.{js,ts,jsx,tsx,mdx}',
    './src/components/**/*.{js,ts,jsx,tsx,mdx}',
    './src/app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        'designer-bg': '#e8eaf0',
        'panel-bg': '#f5f6f8',
        'toolbar-bg': '#2c2f3a',
        'accent': '#4f80ff',
      },
    },
  },
  plugins: [],
};

export default config;
