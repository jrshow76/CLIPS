package com.tulip.iam.keycloak;

import com.tulip.common.core.exception.BusinessException;
import com.tulip.common.security.error.AuthErrorCode;
import com.tulip.iam.config.IamProperties;
import org.springframework.http.HttpEntity;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.stereotype.Component;
import org.springframework.util.LinkedMultiValueMap;
import org.springframework.util.MultiValueMap;
import org.springframework.web.client.RestClientException;
import org.springframework.web.client.RestTemplate;

import java.util.Map;

/**
 * Keycloak 토큰/세션 종료 엔드포인트와 통신하는 어댑터.
 *
 * <p>Authorization Code grant + PKCE 흐름, Refresh Token grant, end-session 을 지원한다.
 * 응답 파싱은 단순화하여 {@code Map<String, Object>} 로 처리한다.</p>
 */
@Component
public class KeycloakClient {

    private final RestTemplate restTemplate;
    private final IamProperties props;

    public KeycloakClient(RestTemplate keycloakRestTemplate, IamProperties props) {
        this.restTemplate = keycloakRestTemplate;
        this.props = props;
    }

    /** Authorization Code 를 토큰으로 교환 (PKCE code_verifier 포함). */
    @SuppressWarnings("unchecked")
    public Map<String, Object> exchangeCode(String code, String redirectUri, String codeVerifier) {
        MultiValueMap<String, String> form = new LinkedMultiValueMap<>();
        form.add("grant_type", "authorization_code");
        form.add("code", code);
        form.add("redirect_uri", redirectUri);
        form.add("client_id", props.keycloak().clientId());
        if (props.keycloak().clientSecret() != null && !props.keycloak().clientSecret().isBlank()) {
            form.add("client_secret", props.keycloak().clientSecret());
        }
        if (codeVerifier != null) {
            form.add("code_verifier", codeVerifier);
        }
        return postForm(props.keycloak().tokenEndpoint(), form);
    }

    /** Refresh Token 으로 회전. */
    public Map<String, Object> refresh(String refreshToken) {
        MultiValueMap<String, String> form = new LinkedMultiValueMap<>();
        form.add("grant_type", "refresh_token");
        form.add("refresh_token", refreshToken);
        form.add("client_id", props.keycloak().clientId());
        if (props.keycloak().clientSecret() != null && !props.keycloak().clientSecret().isBlank()) {
            form.add("client_secret", props.keycloak().clientSecret());
        }
        return postForm(props.keycloak().tokenEndpoint(), form);
    }

    /** Keycloak end-session(로그아웃). */
    public void endSession(String refreshToken) {
        if (props.keycloak().endSessionEndpoint() == null || props.keycloak().endSessionEndpoint().isBlank()) {
            return;
        }
        MultiValueMap<String, String> form = new LinkedMultiValueMap<>();
        form.add("client_id", props.keycloak().clientId());
        if (refreshToken != null) {
            form.add("refresh_token", refreshToken);
        }
        if (props.keycloak().clientSecret() != null && !props.keycloak().clientSecret().isBlank()) {
            form.add("client_secret", props.keycloak().clientSecret());
        }
        HttpHeaders headers = new HttpHeaders();
        headers.setContentType(MediaType.APPLICATION_FORM_URLENCODED);
        try {
            restTemplate.postForEntity(props.keycloak().endSessionEndpoint(),
                    new HttpEntity<>(form, headers), String.class);
        } catch (RestClientException ignored) {
            // end-session 실패는 비치명; 로컬 블랙리스트만 적용
        }
    }

    @SuppressWarnings("unchecked")
    private Map<String, Object> postForm(String url, MultiValueMap<String, String> form) {
        HttpHeaders headers = new HttpHeaders();
        headers.setContentType(MediaType.APPLICATION_FORM_URLENCODED);
        try {
            ResponseEntity<Map> resp = restTemplate.postForEntity(url,
                    new HttpEntity<>(form, headers), Map.class);
            if (resp.getStatusCode().is2xxSuccessful() && resp.getBody() != null) {
                return resp.getBody();
            }
            throw new BusinessException(AuthErrorCode.LOGIN_FAILED,
                    "Keycloak 토큰 엔드포인트 응답 비정상 status=" + resp.getStatusCode());
        } catch (RestClientException ex) {
            throw new BusinessException(AuthErrorCode.LOGIN_FAILED,
                    "Keycloak 통신 실패: " + ex.getMessage());
        }
    }
}
