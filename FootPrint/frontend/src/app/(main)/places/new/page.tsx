import Link from 'next/link';
import PlaceForm from '@/components/place/PlaceForm';

export default function PlaceNewPage() {
  return (
    <>
      {/* 페이지 전용 GNB */}
      <nav className="h-[60px] bg-white border-b border-[#E7E5E4] flex items-center px-6 gap-3 sticky top-0 z-[100]">
        <Link href="/places" className="text-[22px] no-underline text-[#1C1917] leading-none">
          ←
        </Link>
        <span className="text-[17px] font-bold text-[#1C1917]">장소 등록</span>
      </nav>

      <PlaceForm mode="create" />
    </>
  );
}
