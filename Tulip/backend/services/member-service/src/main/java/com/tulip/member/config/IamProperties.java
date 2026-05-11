package com.tulip.member.config;

import org.springframework.boot.context.properties.ConfigurationProperties;

import java.util.HashSet;
import java.util.Set;

/**
 * tulip.iam.* IAM 연동 설정 (JWT issuer / JWKS URI).
 */
@ConfigurationProperties(prefix = "tulip.iam")
public class IamProperties {

    private String issuerUri;
    private String jwksUri;
    private Set<String> expectedAudiences = new HashSet<>();

    public String getIssuerUri() { return issuerUri; }
    public void setIssuerUri(String issuerUri) { this.issuerUri = issuerUri; }
    public String getJwksUri() { return jwksUri; }
    public void setJwksUri(String jwksUri) { this.jwksUri = jwksUri; }
    public Set<String> getExpectedAudiences() { return expectedAudiences; }
    public void setExpectedAudiences(Set<String> expectedAudiences) { this.expectedAudiences = expectedAudiences; }
}
