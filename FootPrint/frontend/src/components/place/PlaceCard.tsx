import Link from 'next/link';
import dayjs from 'dayjs';
import type { PlaceSummary } from '@/types';
import Badge from '@/components/common/Badge';

interface PlaceCardProps {
  place: PlaceSummary;
}

const CATEGORY_COLOR_MAP: Record<string, string> = {
  맛집: 'orange',
  카페: 'blue',
  관광지: 'orange',
  자연: 'green',
  숙소: 'purple',
  쇼핑: 'yellow',
  문화: 'purple',
  기타: 'orange',
};

function getCategoryColor(name: string, color?: string): string {
  if (color) return color;
  return CATEGORY_COLOR_MAP[name] ?? 'orange';
}

export default function PlaceCard({ place }: PlaceCardProps) {
  const formattedDate = dayjs(place.visitedAt).format('YYYY.MM.DD');

  return (
    <Link
      href={`/places/${place.id}`}
      className="block bg-white border border-[#E7E5E4] rounded-[16px] overflow-hidden no-underline text-inherit transition-transform duration-200 hover:-translate-y-1 hover:shadow-[0_12px_32px_rgba(0,0,0,0.10)]"
    >
      {/* 썸네일 */}
      <div className="h-[160px] bg-gradient-to-br from-[#FFF8F0] to-[#FEF3C7] flex items-center justify-center text-[52px] overflow-hidden">
        {place.thumbnailUrl ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={place.thumbnailUrl}
            alt={place.name}
            className="w-full h-full object-cover"
          />
        ) : (
          <span>📍</span>
        )}
      </div>

      {/* 카드 본체 */}
      <div className="p-4">
        {/* 카테고리 배지 */}
        {place.categories.length > 0 && (
          <div className="flex gap-1.5 flex-wrap mb-2.5">
            {place.categories.map((cat) => (
              <Badge
                key={cat.id}
                label={cat.name}
                color={getCategoryColor(cat.name, cat.color)}
              />
            ))}
          </div>
        )}

        <h2 className="text-[16px] font-bold text-[#1C1917] mb-1">{place.name}</h2>

        {place.address && (
          <p className="text-[13px] text-[#78716C] mb-2 truncate">
            {place.address}
          </p>
        )}

        <div className="flex items-center justify-between text-[12px] text-[#A8A29E]">
          <span>{formattedDate}</span>
          {place.rating != null && (
            <span className="text-[#F59E0B] font-semibold text-[13px]">
              ★ {place.rating.toFixed(1)}
            </span>
          )}
        </div>
      </div>
    </Link>
  );
}
