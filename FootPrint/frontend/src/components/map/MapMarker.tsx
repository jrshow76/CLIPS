'use client';

import { useEffect, useRef } from 'react';
import type { PlaceSummary } from '@/types';

interface MapMarkerProps {
  map: KakaoMap;
  place: PlaceSummary;
  onClick?: (place: PlaceSummary) => void;
}

/**
 * 개별 마커 컴포넌트.
 * MapView 내부에서 kakao.maps.Marker를 직접 생성하는 방식을 사용하므로,
 * 이 컴포넌트는 마커 생명주기 관리를 추상화하는 용도이다.
 */
export default function MapMarker({ map, place, onClick }: MapMarkerProps) {
  const markerRef = useRef<KakaoMarker | null>(null);

  useEffect(() => {
    if (!window.kakao?.maps) return;

    const kakao = window.kakao.maps;
    const position = new kakao.LatLng(place.latitude, place.longitude);
    const marker = new kakao.Marker({ position, map });
    markerRef.current = marker;

    if (onClick) {
      kakao.event.addListener(marker, 'click', () => onClick(place));
    }

    return () => {
      marker.setMap(null);
    };
  }, [map, place, onClick]);

  return null;
}
