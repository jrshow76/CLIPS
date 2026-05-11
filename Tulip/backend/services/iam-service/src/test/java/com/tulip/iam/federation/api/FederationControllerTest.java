package com.tulip.iam.federation.api;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.tulip.common.web.advice.GlobalExceptionHandler;
import com.tulip.iam.federation.persistence.InMemoryFederationProviderRepository;
import com.tulip.iam.federation.provider.SamlFederationProvider;
import com.tulip.iam.federation.registry.FederationProviderConfig;
import com.tulip.iam.federation.registry.FederationProviderRegistry;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.setup.MockMvcBuilders;

import java.util.List;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * {@link FederationController} MockMvc 단위 테스트.
 *
 * <p>핵심 검증 포인트:</p>
 * <ul>
 *   <li>GET /providers — 미등록 테넌트에서 빈 리스트 반환</li>
 *   <li>POST /authorize — 미존재 providerId 시 NotFound 응답</li>
 * </ul>
 */
class FederationControllerTest {

    private MockMvc mockMvc;
    private InMemoryFederationProviderRepository repository;
    private ObjectMapper objectMapper;

    @BeforeEach
    void setUp() {
        repository = new InMemoryFederationProviderRepository();
        FederationProviderRegistry registry = new FederationProviderRegistry(
                List.of(new SamlFederationProvider())
        );
        FederationController controller = new FederationController(registry, repository);

        mockMvc = MockMvcBuilders.standaloneSetup(controller)
                .setControllerAdvice(new GlobalExceptionHandler())
                .build();
        objectMapper = new ObjectMapper();
    }

    @Test
    @DisplayName("GET /providers — 미등록 테넌트의 IdP 목록은 빈 배열을 반환한다")
    void listProvidersEmpty() throws Exception {
        mockMvc.perform(get("/api/v1/auth/federation/providers")
                        .param("tenantId", "tnt_001"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.success").value(true))
                .andExpect(jsonPath("$.data").isArray())
                .andExpect(jsonPath("$.data.length()").value(0));
    }

    @Test
    @DisplayName("GET /providers — 등록된 IdP 만 활성화되어 노출된다")
    void listProvidersReturnsRegistered() throws Exception {
        repository.register(new FederationProviderConfig(
                "tnt_001", "saml-default", "SAML", "테스트 대학교 SSO", true));
        repository.register(new FederationProviderConfig(
                "tnt_001", "oidc-disabled", "OIDC", "비활성 OIDC", false));
        repository.register(new FederationProviderConfig(
                "tnt_999", "other-tenant", "SAML", "다른 테넌트", true));

        mockMvc.perform(get("/api/v1/auth/federation/providers")
                        .param("tenantId", "tnt_001"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.success").value(true))
                .andExpect(jsonPath("$.data.length()").value(1))
                .andExpect(jsonPath("$.data[0].providerId").value("saml-default"))
                .andExpect(jsonPath("$.data[0].type").value("SAML"));
    }

    @Test
    @DisplayName("POST /authorize — 미존재 providerId 는 TLP-AUT-FED-404 로 응답한다")
    void authorizeReturnsNotFoundForUnknownProvider() throws Exception {
        FederationAuthorizeRequestBody body = new FederationAuthorizeRequestBody(
                "tnt_001", "nonexistent", "https://opac.example.com/callback", "state-1"
        );

        mockMvc.perform(post("/api/v1/auth/federation/authorize")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsString(body)))
                .andExpect(status().isNotFound())
                .andExpect(jsonPath("$.success").value(false))
                .andExpect(jsonPath("$.code").value("TLP-AUT-FED-404"));
    }

    @Test
    @DisplayName("POST /authorize — 등록된 IdP 호출 시 스텁 어댑터가 TLP-AUT-FED-501 을 던진다")
    void authorizeReturnsNotImplementedForStub() throws Exception {
        repository.register(new FederationProviderConfig(
                "tnt_001", "saml-default", "SAML", "테스트 대학교 SSO", true));

        FederationAuthorizeRequestBody body = new FederationAuthorizeRequestBody(
                "tnt_001", "saml-default", "https://opac.example.com/callback", "state-1"
        );

        mockMvc.perform(post("/api/v1/auth/federation/authorize")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsString(body)))
                .andExpect(status().is(501))
                .andExpect(jsonPath("$.success").value(false))
                .andExpect(jsonPath("$.code").value("TLP-AUT-FED-501"));
    }
}
