'use client';

import { useState, useCallback } from 'react';
import dynamic from 'next/dynamic';
import Link from 'next/link';
import dayjs from 'dayjs';
import type { PlaceSummary } from '@/types';
import { usePlacesInViewport } from '@/lib/hooks/usePlaces';

// 카카오 지도는 SSR 불가 → dynamic import
const MapView = dynamic(() => import('@/components/map/MapView'), { ssr: false });

interface ViewportBounds {
  swLat: number;
  swLng: number;
  neLat: number;
  neLng: number;
}

export default function MapPage() {
  const [bounds, setBounds] = useState<ViewportBounds | null>(null);
  const [selectedPlace, setSelectedPlace] = useState<PlaceSummary | null>(null);
  const [keyword, setKeyword] = useState('');

  const { data: places = [] } = usePlacesInViewport(
    bounds?.swLat ?? 0,
    bounds?.swLng ?? 0,
    bounds?.neLat ?? 0,
    bounds?.neLng ?? 0,
    !!bounds
  );

  const handleBoundsChange = useCallback((b: ViewportBounds) => {
    setBounds(b);
  }, []);

  const handleMarkerClick = useCallback((place: PlaceSummary) => {
    setSelectedPlace(place);
  }, []);

  const filteredPlaces = keyword
    ? places.filter(
        (p) =>
          p.name.includes(keyword) ||
          (p.address?.includes(keyword) ?? false)
      )
    : places;

  return (
    <div className="flex flex-1 h-[calc(100vh-60px)] overflow-hidden">
      {/* 지도 영역 */}
      <MapView
        places={filteredPlaces}
        onBoundsChange={handleBoundsChange}
        onMarkerClick={handleMarkerClick}
        className="flex-1"
      />

      {/* 사이드 패널 */}
      <aside className="w-[360px] bg-white border-l border-[#E7E5E4] flex flex-col overflow-hidden max-md:hidden">
        {/* 헤더 */}
        <div className="px-5 py-4 border-b border-[#F5F5F4] flex items-center justify-between">
          <span className="text-[16px] font-bold text-[#1C1917]">나의 장소</span>
          <span className="text-[13px] text-[#78716C]">{filteredPlaces.length}곳</span>
        </div>

        {/* 검색 */}
        <div className="px-4 py-3 border-b border-[#F5F5F4]">
          <input
            type="search"
            value={keyword}
            onChange={(e) => setKeyword(e.target.value)}
            placeholder="장소명, 주소 검색..."
            className="w-full border-[1.5px] border-[#E7E5E4] rounded-lg px-3.5 py-2.5 text-[14px] outline-none focus:border-[#F97316] placeholder:text-[#A8A29E]"
          />
        </div>

        {/* 장소 목록 */}
        <ul className="flex-1 overflow-y-auto py-2">
          {filteredPlaces.length === 0 ? (
            <li className="text-center py-10 text-[#A8A29E] text-[14px]">
              표시할 장소가 없습니다
            </li>
          ) : (
            filteredPlaces.map((place) => (
              <li
                key={place.id}
                onClick={() => setSelectedPlace(place)}
                className={`flex gap-3 px-4 py-3 cursor-pointer transition-colors ${
                  selectedPlace?.id === place.id
                    ? 'bg-[#FFF8F0]'
                    : 'hover:bg-[#FFF8F0]'
                }`}
              >
                {/* 썸네일 */}
                <div className="w-14 h-14 rounded-[10px] bg-[#F5F5F0] flex items-center justify-center text-[24px] flex-shrink-0 overflow-hidden">
                  {place.thumbnailUrl ? (
                    // eslint-disable-next-line @next/next/no-img-element
                    <img
                      src={place.thumbnailUrl}
                      alt={place.name}
                      className="w-full h-full object-cover rounded-[10px]"
                    />
                  ) : (
                    <span>📍</span>
                  )}
                </div>

                {/* 정보 */}
                <div className="flex-1 min-w-0">
                  <Link
                    href={`/places/${place.id}`}
                    className="text-[14px] font-semibold text-[#1C1917] block truncate hover:text-[#F97316] no-underline"
                    onClick={(e) => e.stopPropagation()}
                  >
                    {place.name}
                  </Link>
                  <p className="text-[12px] text-[#78716C] mt-0.5 truncate">
                    {place.address ?? ''} · {dayjs(place.visitedAt).format('YYYY.MM.DD')}
                  </p>
                  {place.categories.length > 0 && (
                    <span className="inline-block mt-1.5 px-2 py-0.5 rounded-full text-[11px] font-semibold bg-[#FFF8F0] text-[#F97316]">
                      {place.categories[0].name}
                    </span>
                  )}
                </div>
              </li>
            ))
          )}
        </ul>
      </aside>
    </div>
  );
}
