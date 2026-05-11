package com.tulip.iam.federation.api;

import com.tulip.common.core.exception.NotFoundException;
import com.tulip.common.core.response.ApiResponse;
import com.tulip.iam.federation.dto.FederationAuthorizeRequest;
import com.tulip.iam.federation.dto.FederationCallbackPayload;
import com.tulip.iam.federation.dto.FederationLoginContext;
import com.tulip.iam.federation.dto.FederationUserProfile;
import com.tulip.iam.federation.error.IamErrorCode;
import com.tulip.iam.federation.persistence.FederationProviderRepository;
import com.tulip.iam.federation.registry.FederationProviderConfig;
import com.tulip.iam.federation.registry.FederationProviderRegistry;
import com.tulip.iam.federation.spi.FederationProvider;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.validation.Valid;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.util.HashMap;
import java.util.List;
import java.util.Map;

/**
 * 외부 SSO Federation REST 엔드포인트 (Phase 1-B 스텁).
 *
 * <p>경로 prefix: {@code /api/v1/auth/federation}. {@code 03_api_standards.md} 규약에 따라
 * 모든 응답은 {@link ApiResponse} envelope 으로 래핑된다.</p>
 *
 * <p>Phase 1-B 의 모든 인증·콜백 호출은 {@code TLP-AUT-FED-501}
 * ({@link IamErrorCode#FEDERATION_NOT_IMPLEMENTED}) 로 종료된다.
 * 본 컨트롤러는 라우팅·검증·표준 응답 envelope 만 책임진다.</p>
 */
@RestController
@RequestMapping("/api/v1/auth/federation")
public class FederationController {

    private final FederationProviderRegistry registry;
    private final FederationProviderRepository repository;

    public FederationController(FederationProviderRegistry registry,
                                FederationProviderRepository repository) {
        this.registry = registry;
        this.repository = repository;
    }

    /**
     * 테넌트에서 활성화된 IdP 목록을 조회한다.
     *
     * <p>로그인 페이지에서 "OO대학교 SSO 로그인" 버튼을 렌더링할 때 사용한다.</p>
     */
    @GetMapping("/providers")
    public ApiResponse<List<FederationProviderSummary>> listProviders(@RequestParam("tenantId") String tenantId) {
        List<FederationProviderSummary> summaries = repository.findActiveByTenant(tenantId).stream()
                .map(cfg -> new FederationProviderSummary(cfg.providerId(), cfg.type(), cfg.displayName()))
                .toList();
        return ApiResponse.success(summaries);
    }

    /**
     * IdP 로 보낼 인가 요청 정보를 생성한다.
     *
     * <p>Phase 1-B 단계에서는 어댑터가 스텁이므로 어댑터 호출 시점에서
     * {@code TLP-AUT-FED-501} 이 발생한다. (스텁이 의도적으로 던지며,
     * GlobalExceptionHandler 가 envelope 으로 변환)</p>
     */
    @PostMapping("/authorize")
    public ApiResponse<FederationAuthorizeRequest> authorize(@Valid @RequestBody FederationAuthorizeRequestBody body) {
        // 등록 데이터 확인 (스텁: 미존재 시 404)
        FederationProviderConfig config = repository.findByProviderId(body.providerId())
                .orElseThrow(() -> new NotFoundException(
                        IamErrorCode.FEDERATION_PROVIDER_NOT_FOUND,
                        "등록되지 않은 IdP: " + body.providerId()
                ));

        FederationProvider provider = registry.findByProviderId(config.providerId())
                .orElseThrow(() -> new NotFoundException(
                        IamErrorCode.FEDERATION_PROVIDER_NOT_FOUND,
                        "활성화되지 않은 IdP 어댑터: " + config.providerId()
                ));

        FederationLoginContext ctx = new FederationLoginContext(
                body.tenantId(), body.providerId(), body.returnUri(), body.state()
        );
        // Phase 3 에서 실제 구현; 현재는 스텁이 BusinessException 을 던진다.
        FederationAuthorizeRequest authorizeRequest = provider.buildAuthorizeRequest(ctx);
        return ApiResponse.success(authorizeRequest);
    }

    /**
     * IdP 콜백을 수신한다.
     *
     * <p>Phase 3 흐름:</p>
     * <ol>
     *   <li>{@code handleCallback} 으로 사용자 프로필 추출</li>
     *   <li>JIT 가 활성화된 경우 미존재 사용자를 프로비저닝</li>
     *   <li>내부 JWT 발급 (AuthService 위임)</li>
     * </ol>
     *
     * <p>Phase 1-B 에서는 어댑터 스텁이 호출 즉시 501 을 던진다.
     * 본 메서드는 호출 흐름의 자리잡기만 담당하며, 실제 JWT 발급 단계는 TODO 로 둔다.</p>
     */
    @GetMapping("/callback/{providerId}")
    public ApiResponse<FederationCallbackResult> callback(@PathVariable("providerId") String providerId,
                                                          @RequestParam Map<String, String> params,
                                                          HttpServletRequest request) {
        FederationProvider provider = registry.findByProviderId(providerId)
                .orElseThrow(() -> new NotFoundException(
                        IamErrorCode.FEDERATION_PROVIDER_NOT_FOUND,
                        "활성화되지 않은 IdP 어댑터: " + providerId
                ));

        FederationCallbackPayload payload = new FederationCallbackPayload(
                providerId,
                params == null ? Map.of() : new HashMap<>(params),
                null
        );

        // Phase 3 에서 실제 구현; 현재는 스텁이 BusinessException 을 던진다.
        FederationUserProfile profile = provider.handleCallback(payload);

        // TODO(Phase3): JIT 프로비저닝 → iam.AuthService 위임 → 내부 JWT 발급 → Set-Cookie/Redirect
        return ApiResponse.success(new FederationCallbackResult(profile.externalId(), null));
    }

    /**
     * 콜백 처리 결과 (Phase 1-B 시점에는 도달 불가; Phase 3 에서 실제 사용).
     *
     * @param externalId 외부 IdP 가 발급한 사용자 식별자
     * @param accessToken 내부 발급 JWT (Phase 3)
     */
    public record FederationCallbackResult(String externalId, String accessToken) {
    }
}
