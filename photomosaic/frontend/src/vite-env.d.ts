/// <reference types="vite/client" />

// CSS 모듈 타입 선언
declare module '*.module.css' {
  const classes: Record<string, string>;
  export default classes;
}

// SVG 모듈 타입 선언
declare module '*.svg' {
  const src: string;
  export default src;
}
