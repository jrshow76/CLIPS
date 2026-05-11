/**
 * Tulip+ 디자인 토큰 (TypeScript export)
 *
 * Designer 가이드 DSN-02 / DSN-05 기반.
 * 모든 값은 CSS 변수 참조(`var(--...)`)로 노출하여, 라이트/다크 테마 전환을
 * `:root[data-theme="dark"]` 클래스로 처리한다.
 *
 * - 라이브러리 코드에서는 본 토큰을 import 해 사용한다.
 * - Tailwind 사용 시에는 `tailwind-preset` 을 동시 사용한다.
 */

export * from './tokens';
export * from './types';
