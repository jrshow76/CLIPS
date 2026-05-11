export function Footer() {
  return (
    <footer className="border-t border-neutral-200 bg-surface-card py-6">
      <div className="container-opac mx-auto max-w-[1200px] px-4 text-center text-[12px] text-neutral-500 sm:px-6 lg:px-8">
        <p>© 2026 Tulip+ Library System · 모든 이용자를 위한 도서관</p>
        <p className="mt-1">
          <a href="/policy" className="hover:underline">
            이용약관
          </a>{' '}
          ·{' '}
          <a href="/privacy" className="hover:underline">
            개인정보처리방침
          </a>
        </p>
      </div>
    </footer>
  );
}
