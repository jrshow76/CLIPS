# PWA 아이콘 가이드

본 디렉토리는 PWA 매니페스트(`/manifest.webmanifest`)에서 참조되는 아이콘 자산을 저장한다.

## 필요 파일

| 파일 | 크기 | 용도 |
|---|---|---|
| `icon-192.png` | 192x192 | 홈화면 표준 (Android Chrome) |
| `icon-512.png` | 512x512 | 스플래시/스토어용 표준 |
| `icon-192-maskable.png` | 192x192 | Android Adaptive Icon (안전 영역 ≥ 40%) |
| `icon-512-maskable.png` | 512x512 | Android Adaptive Icon (안전 영역 ≥ 40%) |
| `icon-180.png` (선택) | 180x180 | iOS apple-touch-icon |
| `icon-192-placeholder.svg` | - | 빌드 단계 자리표시 (실제 PNG 미배포 시 폴백) |
| `icon-512-placeholder.svg` | - | 빌드 단계 자리표시 |

> 실제 운영 배포 전, Designer 가 브랜드 키트 기반으로 PNG 파일을 생성해 본 디렉토리에 커밋한다.
> 현재는 SVG 자리표시만 포함되어 있어 로컬 빌드 및 PWA 검증은 가능하다(단, iOS/Android 홈화면 추가 아이콘은 PNG 권장).

## PNG 생성 가이드

`scripts/` 또는 디자이너 도구를 사용해 다음 절차로 PNG 를 생성한다.

### 1) SVG → PNG (rsvg-convert / Inkscape / ImageMagick)

```bash
# rsvg-convert (권장: 안티앨리어싱 품질 우수)
rsvg-convert -w 192 -h 192 icon-192-placeholder.svg -o icon-192.png
rsvg-convert -w 512 -h 512 icon-512-placeholder.svg -o icon-512.png

# ImageMagick
convert -background none -density 600 icon-512-placeholder.svg -resize 512x512 icon-512.png
```

### 2) Maskable 아이콘 가이드라인

- 콘텐츠는 중앙 80% 안전 영역 안에 배치 (가장자리 10% 는 OS 가 잘라낼 수 있음)
- 배경은 단색(브랜드 컬러) 권장 — 투명 영역 최소화
- 검증 도구: <https://maskable.app/editor>

### 3) iOS apple-touch-icon

- iOS Safari 는 `<link rel="apple-touch-icon">` 만 인식한다 (매니페스트의 maskable 미지원)
- 180x180 PNG 를 별도 제공하며, 둥근 모서리는 OS 가 자동 적용한다

## 배포 체크리스트

- [ ] icon-192.png, icon-512.png 파일이 존재한다
- [ ] icon-192-maskable.png, icon-512-maskable.png 파일이 존재한다
- [ ] icon-180.png (apple-touch-icon) 파일이 존재한다 (iOS 대응)
- [ ] manifest.webmanifest 의 icons 배열이 실제 파일과 일치한다
- [ ] Lighthouse PWA 감사에서 "Manifest has icons of valid type and size" 가 PASS
