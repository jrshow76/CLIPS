/**
 * Next.js 앱용 ESLint 설정
 *
 * 주의: next/core-web-vitals가 자체적으로 react-hooks 플러그인을 등록하므로
 * 본 설정에서는 react.cjs를 extend하지 않고, base + next만 사용한다.
 */
module.exports = {
  extends: ['./index.cjs', 'next/core-web-vitals', 'prettier'],
  rules: {
    '@next/next/no-html-link-for-pages': 'off',
    'react/react-in-jsx-scope': 'off',
    'react/prop-types': 'off',
  },
};
