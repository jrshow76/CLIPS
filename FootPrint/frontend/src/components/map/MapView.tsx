'use client';

import { useEffect, useRef, useState, useCallback } from 'react';
import type { PlaceSummary } from '@/types';

interface ViewportBounds {
  swLat: number;
  swLng: number;
  neLat: number;
  neLng: number;
}

interface MapViewProps {
  places?: PlaceSummary[];
  onBoundsChange?: (bounds: ViewportBounds) => void;
  onMarkerClick?: (place: PlaceSummary) => void;
  center?: { lat: number; lng: number };
  className?: string;
}

const DEFAULT_CENTER = { lat: 37.5665, lng: 126.978 };
const DEFAULT_LEVEL = 7;

export default function MapView({
  places = [],
  onBoundsChange,
  onMarkerClick,
  center,
  className,
}: MapViewProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<KakaoMap | null>(null);
  const markersRef = useRef<KakaoMarker[]>([]);
  const [isReady, setIsReady] = useState(false);

  // 카카오 지도 SDK 초기화
  useEffect(() => {
    if (typeof window === 'undefined') return;

    const initMap = () => {
      if (!containerRef.current || !window.kakao?.maps) return;
      const kakao = window.kakao.maps;
      const mapCenter = new kakao.LatLng(
        center?.lat ?? DEFAULT_CENTER.lat,
        center?.lng ?? DEFAULT_CENTER.lng
      );
      const map = new kakao.Map(containerRef.current, {
        center: mapCenter,
        level: DEFAULT_LEVEL,
      });
      mapRef.current = map;

      // 뷰포트 변경 이벤트
      kakao.event.addListener(map, 'idle', () => {
        const bounds = map.getBounds();
        const sw = bounds.getSouthWest();
        const ne = bounds.getNorthEast();
        onBoundsChange?.({
          swLat: sw.getLat(),
          swLng: sw.getLng(),
          neLat: ne.getLat(),
          neLng: ne.getLng(),
        });
      });

      setIsReady(true);
    };

    if (window.kakao?.maps) {
      window.kakao.maps.load(initMap);
    } else {
      // SDK 스크립트가 없는 경우 대기
      const timer = setInterval(() => {
        if (window.kakao?.maps) {
          clearInterval(timer);
          window.kakao.maps.load(initMap);
        }
      }, 300);
      return () => clearInterval(timer);
    }
  }, []);

  // 중심 이동
  useEffect(() => {
    if (!mapRef.current || !center || !isReady) return;
    const kakao = window.kakao.maps;
    mapRef.current.setCenter(new kakao.LatLng(center.lat, center.lng));
  }, [center, isReady]);

  // 마커 업데이트
  useEffect(() => {
    if (!mapRef.current || !isReady) return;
    const kakao = window.kakao.maps;

    // 기존 마커 제거
    markersRef.current.forEach((m) => m.setMap(null));
    markersRef.current = [];

    // 새 마커 생성
    places.forEach((place) => {
      const pos = new kakao.LatLng(place.latitude, place.longitude);
      const marker = new kakao.Marker({ position: pos, map: mapRef.current! });
      kakao.event.addListener(marker, 'click', () => {
        onMarkerClick?.(place);
      });
      markersRef.current.push(marker);
    });
  }, [places, isReady, onMarkerClick]);

  const handleCurrentLocation = useCallback(() => {
    if (!mapRef.current) return;
    navigator.geolocation?.getCurrentPosition(({ coords }) => {
      const kakao = window.kakao.maps;
      mapRef.current!.setCenter(new kakao.LatLng(coords.latitude, coords.longitude));
    });
  }, []);

  const handleZoomIn = useCallback(() => {
    if (!mapRef.current) return;
    mapRef.current.setLevel(mapRef.current.getLevel() - 1);
  }, []);

  const handleZoomOut = useCallback(() => {
    if (!mapRef.current) return;
    mapRef.current.setLevel(mapRef.current.getLevel() + 1);
  }, []);

  return (
    <div className={`relative ${className ?? 'flex-1'}`}>
      {/* 카카오 지도 마운트 영역 */}
      <div ref={containerRef} className="w-full h-full bg-[#E8E3D9]" />

      {/* SDK 로드 전 플레이스홀더 */}
      {!isReady && (
        <div className="absolute inset-0 flex flex-col items-center justify-center bg-[#E8E3D9] text-[#A8A29E]">
          <span className="text-[64px] block mb-3">🌍</span>
          <p className="text-[16px]">지도를 불러오는 중...</p>
        </div>
      )}

      {/* 지도 컨트롤 */}
      <div className="absolute top-4 left-4 flex flex-col gap-2 z-10">
        <button
          onClick={handleCurrentLocation}
          title="현재 위치"
          className="w-10 h-10 bg-white border border-[#E7E5E4] rounded-lg flex items-center justify-center text-[18px] shadow-md hover:bg-[#FFF8F0] transition-colors cursor-pointer"
        >
          📍
        </button>
        <button
          onClick={handleZoomIn}
          title="확대"
          className="w-10 h-10 bg-white border border-[#E7E5E4] rounded-lg flex items-center justify-center text-[18px] shadow-md hover:bg-[#FFF8F0] transition-colors cursor-pointer font-bold"
        >
          ＋
        </button>
        <button
          onClick={handleZoomOut}
          title="축소"
          className="w-10 h-10 bg-white border border-[#E7E5E4] rounded-lg flex items-center justify-center text-[18px] shadow-md hover:bg-[#FFF8F0] transition-colors cursor-pointer font-bold"
        >
          －
        </button>
      </div>
    </div>
  );
}
