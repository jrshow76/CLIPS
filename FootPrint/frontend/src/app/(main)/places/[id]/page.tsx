'use client';

import { use } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import dayjs from 'dayjs';
import dynamic from 'next/dynamic';
import { usePlaceDetail, useDeletePlace } from '@/lib/hooks/usePlaces';
import { useToast } from '@/components/common/useToast';
import Badge from '@/components/common/Badge';
import Rating from '@/components/common/Rating';
import Loading from '@/components/common/Loading';
import Button from '@/components/common/Button';
import Modal from '@/components/common/Modal';
import { useState } from 'react';

const MapView = dynamic(() => import('@/components/map/MapView'), { ssr: false });

interface PageProps {
  params: Promise<{ id: string }>;
}

export default function PlaceDetailPage({ params }: PageProps) {
  const { id } = use(params);
  const router = useRouter();
  const toast = useToast();
  const [deleteModalOpen, setDeleteModalOpen] = useState(false);

  const { data: place, isLoading } = usePlaceDetail(Number(id));
  const deletePlace = useDeletePlace();

  const handleDelete = async () => {
    try {
      await deletePlace.mutateAsync(Number(id));
      toast.success('장소가 삭제되었습니다.');
      router.push('/places');
    } catch {
      toast.error('삭제에 실패했습니다.');
      setDeleteModalOpen(false);
    }
  };

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
        <p className="text-[16px]">장소를 찾을 수 없습니다.</p>
        <Link href="/places" className="text-[#F97316] mt-3 inline-block">
          목록으로 돌아가기
        </Link>
      </div>
    );
  }

  const formattedVisitedAt = dayjs(place.visitedAt).format('YYYY년 M월 D일');
  const formattedCreatedAt = dayjs(place.createdAt).format('YYYY.MM.DD');

  return (
    <>
      {/* 상세 전용 GNB */}
      <nav className="h-[60px] bg-white border-b border-[#E7E5E4] flex items-center px-6 gap-3 sticky top-0 z-[100]">
        <Link href="/places" className="text-[22px] no-underline text-[#1C1917] leading-none">
          ←
        </Link>
        <Link href="/map" className="text-[18px] font-extrabold text-[#F97316] no-underline">
          🗺️ 발자국
        </Link>
        <div className="ml-auto flex gap-2">
          <Button
            variant="secondary"
            size="sm"
            onClick={() => router.push(`/places/${id}/edit`)}
          >
            ✏️ 수정
          </Button>
          <Button
            variant="danger"
            size="sm"
            onClick={() => setDeleteModalOpen(true)}
          >
            🗑️ 삭제
          </Button>
        </div>
      </nav>

      <div className="max-w-[800px] mx-auto px-6 py-8">
        {/* 사진 갤러리 */}
        <div className="grid gap-2 rounded-[16px] overflow-hidden mb-7"
          style={{ gridTemplateColumns: place.photos.length > 1 ? '2fr 1fr 1fr' : '1fr', gridTemplateRows: place.photos.length > 1 ? '220px 220px' : '280px' }}
        >
          {place.photos.length === 0 ? (
            <div className="bg-gradient-to-br from-[#FFF8F0] to-[#FDE68A] flex items-center justify-center text-[80px]">
              📍
            </div>
          ) : (
            place.photos.slice(0, 3).map((photo, idx) => (
              <div
                key={photo.id}
                className={idx === 0 ? 'row-span-2 relative' : 'relative'}
              >
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img
                  src={photo.fileUrl}
                  alt={photo.originalName}
                  className="w-full h-full object-cover"
                />
                {idx === 2 && place.photos.length > 3 && (
                  <div className="absolute inset-0 bg-black/35 flex items-center justify-center text-white text-[18px] font-bold cursor-pointer">
                    +{place.photos.length - 3}
                  </div>
                )}
              </div>
            ))
          )}
        </div>

        {/* 장소 상세 카드 */}
        <div className="bg-white border border-[#E7E5E4] rounded-[16px] p-7 mb-5">
          {/* 카테고리 배지 */}
          {place.categories.length > 0 && (
            <div className="flex gap-2 flex-wrap mb-4">
              {place.categories.map((cat) => (
                <Badge key={cat.id} label={cat.name} color={cat.color || 'orange'} />
              ))}
            </div>
          )}

          <h1 className="text-[28px] font-extrabold text-[#1C1917] mb-1.5">{place.name}</h1>

          {place.address && (
            <p className="text-[15px] text-[#78716C] mb-5">📍 {place.address}</p>
          )}

          {/* 메타 정보 */}
          <div className="flex gap-6 flex-wrap border-t border-[#F5F5F4] pt-5 mb-5">
            <div className="flex flex-col gap-1">
              <span className="text-[12px] text-[#A8A29E] font-semibold uppercase tracking-wide">방문일</span>
              <span className="text-[15px] font-bold text-[#1C1917]">{formattedVisitedAt}</span>
            </div>
            {place.rating != null && (
              <div className="flex flex-col gap-1">
                <span className="text-[12px] text-[#A8A29E] font-semibold uppercase tracking-wide">평점</span>
                <div className="flex items-center gap-1">
                  <Rating value={place.rating} readOnly size="sm" />
                  <span className="text-[15px] font-bold text-[#1C1917]">{place.rating.toFixed(1)}</span>
                </div>
              </div>
            )}
            <div className="flex flex-col gap-1">
              <span className="text-[12px] text-[#A8A29E] font-semibold uppercase tracking-wide">등록일</span>
              <span className="text-[15px] font-bold text-[#1C1917]">{formattedCreatedAt}</span>
            </div>
          </div>

          {/* 메모 */}
          {place.memo && (
            <div className="border-t border-[#F5F5F4] pt-5">
              <p className="text-[13px] font-bold text-[#A8A29E] mb-2.5">📝 메모</p>
              <p className="text-[15px] text-[#44403C] leading-relaxed whitespace-pre-wrap">
                {place.memo}
              </p>
            </div>
          )}

          {/* 태그 */}
          {place.tags.length > 0 && (
            <div className="flex gap-2 flex-wrap mt-5 pt-5 border-t border-[#F5F5F4]">
              {place.tags.map((tag) => (
                <span
                  key={tag}
                  className="px-3 py-1 rounded-full bg-[#F5F5F0] text-[#78716C] text-[13px] font-medium"
                >
                  #{tag}
                </span>
              ))}
            </div>
          )}
        </div>

        {/* 미니 지도 */}
        <div className="bg-white border border-[#E7E5E4] rounded-[16px] overflow-hidden">
          <div className="h-[200px]">
            <MapView
              places={[place]}
              center={{ lat: place.latitude, lng: place.longitude }}
              className="w-full h-full"
            />
          </div>
          <div className="px-5 py-3.5 flex items-center justify-between text-[13px] text-[#78716C]">
            <span>
              {place.latitude.toFixed(5)}°N, {place.longitude.toFixed(5)}°E
            </span>
            <Link href="/map" className="text-[#F97316] font-semibold no-underline">
              지도에서 보기 →
            </Link>
          </div>
        </div>
      </div>

      {/* 삭제 확인 모달 */}
      <Modal
        isOpen={deleteModalOpen}
        onClose={() => setDeleteModalOpen(false)}
        title="장소 삭제"
      >
        <p className="text-[15px] text-[#44403C] mb-6">
          <strong>{place.name}</strong>을(를) 정말 삭제하시겠습니까?
          <br />
          <span className="text-[13px] text-[#A8A29E]">삭제한 데이터는 복구할 수 없습니다.</span>
        </p>
        <div className="flex gap-3">
          <Button
            variant="secondary"
            size="md"
            fullWidth
            onClick={() => setDeleteModalOpen(false)}
          >
            취소
          </Button>
          <Button
            variant="danger"
            size="md"
            fullWidth
            loading={deletePlace.isPending}
            onClick={handleDelete}
          >
            삭제
          </Button>
        </div>
      </Modal>
    </>
  );
}
