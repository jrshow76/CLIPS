/* eslint-disable @typescript-eslint/no-explicit-any */
declare global {
  interface KakaoMapOptions {
    center: KakaoLatLng;
    level: number;
  }

  interface KakaoMap {
    setCenter: (latlng: KakaoLatLng) => void;
    getCenter: () => KakaoLatLng;
    setLevel: (level: number) => void;
    getLevel: () => number;
    getBounds: () => KakaoLatLngBounds;
    relayout: () => void;
  }

  interface KakaoLatLng {
    getLat: () => number;
    getLng: () => number;
  }

  interface KakaoLatLngBounds {
    getSouthWest: () => KakaoLatLng;
    getNorthEast: () => KakaoLatLng;
    extend: (latlng: KakaoLatLng) => void;
  }

  interface KakaoMarker {
    setMap: (map: KakaoMap | null) => void;
    getPosition: () => KakaoLatLng;
  }

  interface KakaoInfoWindow {
    open: (map: KakaoMap, marker: KakaoMarker) => void;
    close: () => void;
  }

  interface Window {
    kakao: {
      maps: {
        Map: new (container: HTMLElement, options: KakaoMapOptions) => KakaoMap;
        Marker: new (options: { position: KakaoLatLng; map?: KakaoMap }) => KakaoMarker;
        LatLng: new (lat: number, lng: number) => KakaoLatLng;
        LatLngBounds: new () => KakaoLatLngBounds;
        InfoWindow: new (options: { content: string }) => KakaoInfoWindow;
        event: {
          addListener: (target: any, type: string, handler: (...args: any[]) => void) => void;
          removeListener: (target: any, type: string, handler: (...args: any[]) => void) => void;
        };
        load: (callback: () => void) => void;
      };
    };
  }
}

export {};
