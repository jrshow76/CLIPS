/**
 * 루트 ESLint 설정
 * 각 패키지/앱은 `extends`로 `@tulip/eslint-config`를 사용한다.
 */
module.exports = {
  root: true,
  extends: ['./packages/eslint-config/index.cjs'],
  ignorePatterns: ['node_modules', 'dist', '.next', '.turbo', 'build'],
};
