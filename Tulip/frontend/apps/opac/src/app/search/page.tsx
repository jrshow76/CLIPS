import { PageHeader, SearchBar } from '@tulip/ui';

import { EmptyPlaceholder } from './_components/EmptyPlaceholder';

export const metadata = { title: '검색 결과 — Tulip+ OPAC' };

interface SearchPageProps {
  searchParams: Promise<{ q?: string }>;
}

export default async function SearchPage({ searchParams }: SearchPageProps) {
  const params = await searchParams;
  const q = params.q ?? '';

  return (
    <div className="container-opac mx-auto max-w-[1200px] px-4 py-6 sm:px-6 lg:px-8">
      <PageHeader
        title="검색 결과"
        description={q ? `"${q}"에 대한 검색 결과입니다.` : '검색어를 입력해 주세요.'}
      />
      <div className="mt-4">
        <SearchBar defaultValue={q} placeholder="서명·저자·키워드로 검색" />
      </div>
      <div className="mt-6">
        <EmptyPlaceholder />
      </div>
    </div>
  );
}
