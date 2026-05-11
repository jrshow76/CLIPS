package com.tulip.member.api;

import com.tulip.common.core.exception.BusinessException;
import com.tulip.common.core.page.Pagination;
import com.tulip.common.core.response.ApiResponse;
import com.tulip.common.core.response.ResponseMeta;
import com.tulip.common.security.principal.TulipUserPrincipal;
import com.tulip.member.application.MemberCardService;
import com.tulip.member.application.MemberService;
import com.tulip.member.dto.MemberDtos;
import com.tulip.member.error.MemberErrorCode;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.validation.Valid;
import org.springframework.http.ResponseEntity;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.security.core.Authentication;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PatchMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.net.URI;
import java.util.List;

/**
 * 회원 도메인 REST 컨트롤러.
 *
 * <p>{@code /api/v1/members} 하위 엔드포인트를 노출한다. 메서드 단위 {@code @PreAuthorize} 로
 * 권한을 강제하며, {@code /me} 계열은 본인 자격만 사용한다 ({@code 05_security_and_auth.md} §3).</p>
 */
@RestController
@RequestMapping("/api/v1/members")
@Tag(name = "members", description = "회원·회원증·동의 관리")
public class MemberController {

    private static final String STAFF_ROLES =
            "hasAnyRole('LIB_ADMIN','LIBRARIAN','TENANT_ADMIN','SYS_ADMIN')";

    private final MemberService memberService;
    private final MemberCardService cardService;

    public MemberController(MemberService memberService, MemberCardService cardService) {
        this.memberService = memberService;
        this.cardService = cardService;
    }

    /* ============================== Staff endpoints ============================== */

    @PostMapping
    @PreAuthorize(STAFF_ROLES)
    @Operation(summary = "회원 등록")
    public ResponseEntity<ApiResponse<MemberDtos.MemberResponse>> create(
            @Valid @RequestBody MemberDtos.CreateMemberRequest req,
            Authentication auth) {
        TulipUserPrincipal p = principal(auth);
        Long tenantId = requireTenantId(p);
        Long createdBy = parseId(p.userId());

        MemberDtos.MemberResponse created = memberService.register(tenantId, createdBy, req);
        return ResponseEntity
                .created(URI.create("/api/v1/members/" + created.id()))
                .body(ApiResponse.success(created));
    }

    @GetMapping
    @PreAuthorize(STAFF_ROLES)
    @Operation(summary = "회원 검색")
    public ApiResponse<List<MemberDtos.MemberResponse>> search(
            @RequestParam(required = false) String q,
            @RequestParam(required = false) String status,
            @RequestParam(required = false) Long libraryId,
            @RequestParam(required = false) String memberTypeCode,
            @RequestParam(defaultValue = "1") int page,
            @RequestParam(defaultValue = "20") int size) {
        MemberDtos.MemberSearchCriteria criteria =
                new MemberDtos.MemberSearchCriteria(q, status, libraryId, memberTypeCode);
        MemberService.SearchResult result = memberService.search(criteria, Pagination.offset(page, size));
        ResponseMeta meta = ResponseMeta.offset(result.totalElements(),
                result.pagination().page(), result.pagination().size());
        return ApiResponse.success(result.items(), meta);
    }

    @GetMapping("/{id}")
    @PreAuthorize(STAFF_ROLES + " or #id == T(java.lang.Long).parseLong(principal.userId)")
    @Operation(summary = "회원 단건 조회")
    public ApiResponse<MemberDtos.MemberResponse> get(@PathVariable Long id) {
        return ApiResponse.success(memberService.get(id));
    }

    @PatchMapping("/{id}")
    @PreAuthorize(STAFF_ROLES)
    @Operation(summary = "회원 정보 수정")
    public ApiResponse<MemberDtos.MemberResponse> update(
            @PathVariable Long id,
            @Valid @RequestBody MemberDtos.UpdateMemberRequest req,
            Authentication auth) {
        TulipUserPrincipal p = principal(auth);
        return ApiResponse.success(
                memberService.update(requireTenantId(p), id, parseId(p.userId()), req));
    }

    @DeleteMapping("/{id}")
    @PreAuthorize(STAFF_ROLES)
    @Operation(summary = "회원 소프트 삭제")
    public ResponseEntity<ApiResponse<Void>> delete(@PathVariable Long id, Authentication auth) {
        TulipUserPrincipal p = principal(auth);
        memberService.softDelete(requireTenantId(p), id);
        return ResponseEntity.noContent().build();
    }

    /* ============================== Cards ============================== */

    @PostMapping("/{id}/cards")
    @PreAuthorize(STAFF_ROLES)
    @Operation(summary = "회원증 발급")
    public ResponseEntity<ApiResponse<MemberDtos.CardResponse>> issueCard(
            @PathVariable Long id,
            @Valid @RequestBody MemberDtos.IssueCardRequest req,
            Authentication auth) {
        TulipUserPrincipal p = principal(auth);
        MemberDtos.CardResponse card = cardService.issue(requireTenantId(p), id, parseId(p.userId()), req);
        return ResponseEntity.created(URI.create("/api/v1/members/cards/" + card.id()))
                .body(ApiResponse.success(card));
    }

    @GetMapping("/{id}/cards")
    @PreAuthorize(STAFF_ROLES + " or #id == T(java.lang.Long).parseLong(principal.userId)")
    @Operation(summary = "회원의 카드 목록")
    public ApiResponse<List<MemberDtos.CardResponse>> listCards(@PathVariable Long id) {
        return ApiResponse.success(cardService.listByMember(id));
    }

    @PatchMapping("/cards/{cardId}")
    @PreAuthorize(STAFF_ROLES)
    @Operation(summary = "회원증 상태/만료 변경")
    public ApiResponse<MemberDtos.CardResponse> updateCard(
            @PathVariable Long cardId,
            @Valid @RequestBody MemberDtos.UpdateCardRequest req,
            Authentication auth) {
        TulipUserPrincipal p = principal(auth);
        return ApiResponse.success(
                cardService.updateCard(requireTenantId(p), cardId, parseId(p.userId()), req));
    }

    /* ============================== Consent ============================== */

    @PostMapping("/{id}/consents")
    @PreAuthorize(STAFF_ROLES + " or #id == T(java.lang.Long).parseLong(principal.userId)")
    @Operation(summary = "동의 등록")
    public ResponseEntity<ApiResponse<MemberDtos.ConsentResponse>> addConsent(
            @PathVariable Long id,
            @Valid @RequestBody MemberDtos.ConsentInput input,
            Authentication auth) {
        TulipUserPrincipal p = principal(auth);
        MemberDtos.ConsentResponse resp = memberService.addConsent(
                requireTenantId(p), id, parseId(p.userId()), input);
        return ResponseEntity.created(URI.create("/api/v1/members/" + id + "/consents/" + resp.id()))
                .body(ApiResponse.success(resp));
    }

    @GetMapping("/{id}/consents")
    @PreAuthorize(STAFF_ROLES + " or #id == T(java.lang.Long).parseLong(principal.userId)")
    @Operation(summary = "동의 이력 조회")
    public ApiResponse<List<MemberDtos.ConsentResponse>> listConsents(@PathVariable Long id) {
        return ApiResponse.success(memberService.listConsents(id));
    }

    /* ============================== /me (본인) ============================== */

    @GetMapping("/me")
    @PreAuthorize("hasRole('MEMBER') or " + STAFF_ROLES)
    @Operation(summary = "본인 회원 정보 조회")
    public ApiResponse<MemberDtos.MemberResponse> me(Authentication auth) {
        TulipUserPrincipal p = principal(auth);
        Long id = parseId(p.userId());
        return ApiResponse.success(memberService.get(id));
    }

    @PatchMapping("/me")
    @PreAuthorize("hasRole('MEMBER')")
    @Operation(summary = "본인 정보 수정 (제한된 필드)")
    public ApiResponse<MemberDtos.MemberResponse> updateMe(
            @Valid @RequestBody MemberDtos.UpdateMemberRequest req,
            Authentication auth) {
        TulipUserPrincipal p = principal(auth);
        Long id = parseId(p.userId());
        // 본인 수정은 status 변경 불가 (사서 권한 필요)
        MemberDtos.UpdateMemberRequest safe = new MemberDtos.UpdateMemberRequest(
                req.name(), req.email(), req.phone(), req.birthdate(),
                null, null, req.address(), null);
        return ApiResponse.success(memberService.update(requireTenantId(p), id, id, safe));
    }

    @GetMapping("/me/cards")
    @PreAuthorize("hasRole('MEMBER')")
    @Operation(summary = "본인 카드 목록")
    public ApiResponse<List<MemberDtos.CardResponse>> myCards(Authentication auth) {
        TulipUserPrincipal p = principal(auth);
        Long id = parseId(p.userId());
        return ApiResponse.success(cardService.listByMember(id));
    }

    /* ============================== Helpers ============================== */

    private static TulipUserPrincipal principal(Authentication auth) {
        if (auth == null || !(auth.getPrincipal() instanceof TulipUserPrincipal p)) {
            throw new BusinessException(MemberErrorCode.MEMBER_FORBIDDEN_SELF);
        }
        return p;
    }

    private static Long requireTenantId(TulipUserPrincipal p) {
        try {
            return Long.parseLong(p.tenantId());
        } catch (Exception e) {
            throw new BusinessException(MemberErrorCode.MEMBER_FORBIDDEN_SELF);
        }
    }

    private static Long parseId(String raw) {
        try {
            return Long.parseLong(raw);
        } catch (Exception e) {
            return null;
        }
    }
}
