'use client';

import { use } from 'react';
import Link from 'next/link';
import { usePlaceDetail } from '@/lib/hooks/usePlaces';
import PlaceForm from '@/components/place/PlaceForm';
import Loading from '@/components/common/Loading';

interface PageProps {
  params: Promise<{ id: string }>;
}

export default function PlaceEditPage({ params }: PageProps) {
  const { id } = use(params);
  const { data: place, isLoading } = usePlaceDetail(Number(id));

  if (isLoading) {
    return (
      <div className="flex justify-center items-center py-20">
        <Loading size="lg" />
      </div>
    );
  }

  if (!place) {
    return (
      <div className="text-center py-20 text-[#A8A29E]">
        <p>장소를 찾을 수 없습니다.</p>
        <Link href="/places" className="text-[#F97316] mt-3 inline-block">
          목록으로 돌아가기
        </Link>
      </div>
    );
  }

  return (
    <>
      {/* 페이지 전용 GNB */}
      <nav className="h-[60px] bg-white border-b border-[#E7E5E4] flex items-center px-6 gap-3 sticky top-0 z-[100]">
        <Link
          href={`/places/${id}`}
          className="text-[22px] no-underline text-[#1C1917] leading-none"
        >
          ←
        </Link>
        <span className="text-[17px] font-bold text-[#1C1917]">장소 수정</span>
      </nav>

      <PlaceForm mode="edit" defaultValues={place} />
    </>
  );
}
