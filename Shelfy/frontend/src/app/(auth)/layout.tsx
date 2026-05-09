/**
 * 인증 페이지 레이아웃
 * GNB를 숨기고 인증 전용 레이아웃 적용
 * (auth) 라우트 그룹은 URL에 영향을 주지 않음
 */

export default function AuthLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <div
      style={{
        minHeight: '100vh',
        background: 'var(--color-bg-base)',
      }}
    >
      {children}
    </div>
  )
}
