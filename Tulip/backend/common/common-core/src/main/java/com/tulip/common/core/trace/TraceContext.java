package com.tulip.common.core.trace;

import org.slf4j.MDC;

import java.security.SecureRandom;
import java.util.HexFormat;

/**
 * W3C Trace Context 표준에 따른 traceparent 발급/조회 유틸.
 *
 * <p>형식: {@code <version>-<trace-id 16바이트>-<span-id 8바이트>-<flags>}.
 * SLF4J MDC 키 {@code traceId} 로 로깅 파이프라인에 전파된다.</p>
 */
public final class TraceContext {

    public static final String MDC_TRACE_ID = "traceId";
    public static final String MDC_TENANT_ID = "tenantId";
    public static final String MDC_USER_ID = "userId";
    public static final String HEADER_TRACEPARENT = "traceparent";
    public static final String HEADER_TRACE_ID = "X-Trace-Id";

    private static final SecureRandom RANDOM = new SecureRandom();
    private static final HexFormat HEX = HexFormat.of();

    private TraceContext() {
    }

    /** 새 traceparent 문자열을 생성한다 (W3C v00). */
    public static String newTraceParent() {
        byte[] traceId = new byte[16];
        byte[] spanId = new byte[8];
        RANDOM.nextBytes(traceId);
        RANDOM.nextBytes(spanId);
        return "00-" + HEX.formatHex(traceId) + "-" + HEX.formatHex(spanId) + "-01";
    }

    /** traceparent 또는 임의 문자열에서 traceId 만 추출한다. */
    public static String extractTraceId(String traceParent) {
        if (traceParent == null || traceParent.isBlank()) {
            return null;
        }
        String[] parts = traceParent.split("-");
        return parts.length >= 2 ? parts[1] : traceParent;
    }

    /** 현재 스레드 MDC 에 traceId 를 설정한다. */
    public static void putTraceId(String traceId) {
        if (traceId != null && !traceId.isBlank()) {
            MDC.put(MDC_TRACE_ID, traceId);
        }
    }

    /** MDC 에서 현재 traceId 를 반환한다. */
    public static String currentTraceId() {
        return MDC.get(MDC_TRACE_ID);
    }

    /** MDC 의 모든 trace/tenant/user 키를 제거한다. */
    public static void clear() {
        MDC.remove(MDC_TRACE_ID);
        MDC.remove(MDC_TENANT_ID);
        MDC.remove(MDC_USER_ID);
    }
}
