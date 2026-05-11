import { Badge, SearchBar } from '@tulip/ui';
import Link from 'next/link';

export default function OpacHomePage() {
  return (
    <div>
      {/* Hero — 큰 검색바 */}
      <section className="bg-gradient-to-b from-primary-50 to-surface-app py-12 sm:py-16">
        <div className="container-opac mx-auto max-w-[1000px] px-4 sm:px-6 lg:px-8">
          <h1 className="text-center text-display text-neutral-900">
            지식을 피우다 <span aria-hidden="true">🌷</span>
          </h1>
          <p className="mt-3 text-center text-[16px] text-neutral-700">
            도서, 논문, 영상 — 우리 도서관의 모든 자료를 한 번에 검색하세요.
          </p>
          <div className="mt-8">
            <SearchBar variant="hero" placeholder="서명·저자·키워드로 검색" />
          </div>
          <div className="mt-4 flex flex-wrap items-center justify-center gap-2 text-[12px] text-neutral-600">
            <span>추천:</span>
            {['디자인 시스템', '데이터 분석', '한강', 'AI'].map((kw) => (
              <Badge key={kw} tone="primary" variant="soft" size="sm">
                <Link href={`/search?q=${encodeURIComponent(kw)}`}>{kw}</Link>
              </Badge>
            ))}
          </div>
        </div>
      </section>

      {/* 신착·인기 자리표시자 */}
      <section className="container-opac mx-auto max-w-[1200px] px-4 py-10 sm:px-6 lg:px-8">
        <div className="grid gap-8 md:grid-cols-2">
          <PlaceholderBlock title="이번 주 신착도서" description="새로 들어온 자료를 만나보세요." />
          <PlaceholderBlock title="이용자 인기 자료" description="이번 달 가장 많이 대출된 자료." />
        </div>
      </section>
    </div>
  );
}

function PlaceholderBlock({ title, description }: { title: string; description: string }) {
  return (
    <article className="rounded-2xl border border-neutral-200 bg-surface-card p-6 shadow-sm">
      <header>
        <h2 className="text-h2 text-neutral-900">{title}</h2>
        <p className="mt-1 text-[14px] text-neutral-600">{description}</p>
      </header>
      <div className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <div
            key={i}
            className="aspect-[3/4] rounded-lg bg-neutral-100"
            aria-label={`자료 자리표시자 ${i + 1}`}
          />
        ))}
      </div>
    </article>
  );
}
