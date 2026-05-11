/**
 * 속성 기반(ABAC) 접근 제어 보조 모듈.
 *
 * <p>{@code 05_security_and_auth.md} §3.4 의 tenantId·branchId·timeWindow 등 속성 평가 helper 와
 * Spring Security {@code @PreAuthorize} SpEL 내에서 호출 가능한 Voter 빈을 제공한다.</p>
 *
 * <h3>표준 사용 패턴 (BackendDev 가이드)</h3>
 * <pre>
 *   &#64;PreAuthorize("hasRole('LIB_ADMIN') and &#64;tenantAccessVoter.canAccessCurrent(principal)")
 *   public ResponseEntity&lt;...&gt; updateMember(...) { ... }
 *
 *   &#64;PreAuthorize("hasAuthority('SCOPE_cir:write') and &#64;tenantAccessVoter.canAccessBranch(principal, #branchId)")
 *   public ResponseEntity&lt;...&gt; checkout(&#64;PathVariable String branchId, ...) { ... }
 * </pre>
 *
 * <p>모든 도메인 컨트롤러는 1) 역할 검증, 2) 테넌트 검증, 3) (필요 시) branch 검증 3중을 의무화한다.</p>
 */
package com.tulip.common.security.abac;
