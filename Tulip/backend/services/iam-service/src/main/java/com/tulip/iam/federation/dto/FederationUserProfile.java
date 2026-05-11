package com.tulip.iam.federation.dto;

import java.util.List;
import java.util.Map;

/**
 * 외부 IdP 로부터 수신한 사용자 프로필 정보.
 *
 * <p>{@link com.tulip.iam.federation.spi.FederationProvider#handleCallback} 의 결과로 반환되며,
 * JIT(Just-In-Time) 프로비저닝 또는 기존 사용자 매핑의 입력값으로 사용된다.</p>
 *
 * <p>외부 IdP 가 전달하는 속성은 프로토콜·운영기관별로 매우 이질적이므로,
 * 표준 필드는 최소화하고 나머지는 {@code attributes} 에 자유롭게 담는다.</p>
 *
 * @param externalId   IdP 가 발급한 사용자 고유 식별자 (필수, 변경 불가 권장)
 * @param email        사용자 이메일 (있는 경우, JIT 매핑 후보)
 * @param displayName  표시 이름 (있는 경우)
 * @param attributes   IdP 가 추가로 제공한 원본 속성 (raw, 마스킹 후 audit 로깅)
 * @param roles        IdP 측 역할/그룹 클레임 (Tulip+ 역할로의 매핑은 별도 정책)
 */
public record FederationUserProfile(
        String externalId,
        String email,
        String displayName,
        Map<String, Object> attributes,
        List<String> roles
) {

    /** attributes·roles 없이 식별자·이메일·이름만으로 생성하는 편의 생성자. */
    public FederationUserProfile(String externalId, String email, String displayName) {
        this(externalId, email, displayName, Map.of(), List.of());
    }
}
