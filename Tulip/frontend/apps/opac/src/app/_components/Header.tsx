import Link from 'next/link';

import { NavLinks } from './NavLinks';

export function Header() {
  return (
    <header className="sticky top-0 z-sticky border-b border-neutral-200 bg-surface-card">
      <div className="container-opac mx-auto flex h-16 max-w-[1200px] items-center justify-between gap-4 px-4 sm:px-6 lg:px-8">
        <Link href="/" className="flex items-center gap-2 text-neutral-900 hover:opacity-80">
          <span aria-hidden="true" className="text-2xl">
            🌷
          </span>
          <span className="text-h3 font-bold">Tulip+ 도서관</span>
        </Link>
        <NavLinks />
      </div>
    </header>
  );
}
