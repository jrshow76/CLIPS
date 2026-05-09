'use client';

import { useCallback } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { usePlaceList } from '@/lib/hooks/usePlaces';
import { useCategories } from '@/lib/hooks/useCategories';
import PlaceCard from './PlaceCard';
import Loading from '@/components/common/Loading';
import { cn } from '@/lib/utils';

export default function PlaceList() {
  const router = useRouter();
  const searchParams = useSearchParams();

  const keyword = searchParams.get('keyword') ?? '';
  const categoryId = searchParams.get('category') ? Number(searchParams.get('category')) : undefined;
  const page = searchParams.get('page') ? Number(searchParams.get('page')) : 0;

  const { data: placePage, isLoading } = usePlaceList({
    keyword: keyword || undefined,
    categoryIds: categoryId ? [categoryId] : undefined,
    page,
    size: 12,
  });

  const { data: categories = [] } = useCategories();

  const updateQuery = useCallback(
    (key: string, value: string | null) => {
      const params = new URLSearchParams(searchParams.toString());
      if (value) {
        params.set(key, value);
      } else {
        params.delete(key);
      }
      params.delete('page');
      router.push(`?${params.toString()}`);
    },
    [router, searchParams]
  );

  const places = placePage?.content ?? [];
  const total = placePage?.totalElements ?? 0;
  const totalPages = placePage?.totalPages ?? 1;

  return (
    <div className="max-w-[1100px] mx-auto px-6 py-8">
      {/* 페이지 헤더 */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-[24px] font-extrabold text-[#1C1917]">나의 발자국</h1>
          <p className="text-[14px] text-[#78716C] mt-1">
            총 {total}곳을 방문했습니다
          </p>
        </div>
      </div>

      {/* 필터 바 */}
      <div className="bg-white border border-[#E7E5E4] rounded-[12px] px-5 py-4 flex gap-3 flex-wrap items-center mb-6">
        <input
          type="search"
          defaultValue={keyword}
          placeholder="장소명, 주소로 검색..."
          className="flex-1 min-w-[200px] border-[1.5px] border-[#E7E5E4] rounded-lg px-3.5 py-2 text-[14px] outline-none focus:border-[#F97316] placeholder:text-[#A8A29E]"
          onChange={(e) => {
            const v = e.target.value;
            if (!v) updateQuery('keyword', null);
          }}
          onKeyDown={(e) => {
            if (e.key === 'Enter') {
              updateQuery('keyword', (e.target as HTMLInputElement).value || null);
            }
          }}
        />
        <div className="flex gap-2 flex-wrap">
          <button
            onClick={() => updateQuery('category', null)}
            className={cn(
              'px-3.5 py-1.5 rounded-full text-[13px] font-semibold border-[1.5px] transition-colors cursor-pointer',
              !categoryId
                ? 'border-[#F97316] bg-[#FFF8F0] text-[#F97316]'
                : 'border-[#E7E5E4] bg-white text-[#78716C] hover:border-[#F97316] hover:text-[#F97316]'
            )}
          >
            전체
          </button>
          {categories.map((cat) => (
            <button
              key={cat.id}
              onClick={() => updateQuery('category', String(cat.id))}
              className={cn(
                'px-3.5 py-1.5 rounded-full text-[13px] font-semibold border-[1.5px] transition-colors cursor-pointer',
                categoryId === cat.id
                  ? 'border-[#F97316] bg-[#FFF8F0] text-[#F97316]'
                  : 'border-[#E7E5E4] bg-white text-[#78716C] hover:border-[#F97316] hover:text-[#F97316]'
              )}
            >
              {cat.name}
            </button>
          ))}
        </div>
      </div>

      {/* 장소 그리드 */}
      {isLoading ? (
        <div className="flex justify-center py-20">
          <Loading size="lg" />
        </div>
      ) : places.length === 0 ? (
        <div className="text-center py-20 text-[#A8A29E]">
          <span className="text-[56px] block mb-4">🗺️</span>
          <p className="text-[16px] mb-5">아직 등록된 장소가 없습니다</p>
        </div>
      ) : (
        <div className="grid grid-cols-[repeat(auto-fill,minmax(280px,1fr))] gap-5">
          {places.map((place) => (
            <PlaceCard key={place.id} place={place} />
          ))}
        </div>
      )}

      {/* 페이지네이션 */}
      {totalPages > 1 && (
        <div className="flex justify-center gap-2 mt-8">
          {Array.from({ length: totalPages }, (_, i) => (
            <button
              key={i}
              onClick={() => {
                const params = new URLSearchParams(searchParams.toString());
                params.set('page', String(i));
                router.push(`?${params.toString()}`);
              }}
              className={cn(
                'w-9 h-9 rounded-lg text-[14px] font-semibold transition-colors cursor-pointer',
                i === page
                  ? 'bg-[#F97316] text-white'
                  : 'bg-white border border-[#E7E5E4] text-[#78716C] hover:border-[#F97316] hover:text-[#F97316]'
              )}
            >
              {i + 1}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
