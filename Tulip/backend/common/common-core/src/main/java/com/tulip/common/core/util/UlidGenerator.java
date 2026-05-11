package com.tulip.common.core.util;

import java.security.SecureRandom;
import java.time.Instant;

/**
 * ULID(Universally Unique Lexicographically Sortable Identifier) 발급 유틸.
 *
 * <p>외부 공개 식별자({@code public_id}) 가 필요한 도메인(서지·회원 URL 노출)에서 사용한다.
 * BIGINT IDENTITY 가 기본 PK 이므로 본 ULID 는 보조 식별자다.
 * Crockford Base32, 128bit (48bit 시간 + 80bit 랜덤).</p>
 */
public final class UlidGenerator {

    private static final char[] ENCODING = "0123456789ABCDEFGHJKMNPQRSTVWXYZ".toCharArray();
    private static final SecureRandom RANDOM = new SecureRandom();

    private UlidGenerator() {
    }

    /** 새 ULID 문자열(26자)을 발급한다. */
    public static String newUlid() {
        long timestamp = Instant.now().toEpochMilli();
        byte[] random = new byte[10];
        RANDOM.nextBytes(random);
        return encodeTime(timestamp) + encodeRandom(random);
    }

    private static String encodeTime(long timestamp) {
        char[] buf = new char[10];
        for (int i = 9; i >= 0; i--) {
            buf[i] = ENCODING[(int) (timestamp & 0x1f)];
            timestamp >>>= 5;
        }
        return new String(buf);
    }

    private static String encodeRandom(byte[] random) {
        char[] buf = new char[16];
        // 80bit 를 5bit 단위로 16자 인코딩
        long high = ((long) (random[0] & 0xff) << 32)
                | ((long) (random[1] & 0xff) << 24)
                | ((long) (random[2] & 0xff) << 16)
                | ((long) (random[3] & 0xff) << 8)
                | (random[4] & 0xff);
        long low = ((long) (random[5] & 0xff) << 32)
                | ((long) (random[6] & 0xff) << 24)
                | ((long) (random[7] & 0xff) << 16)
                | ((long) (random[8] & 0xff) << 8)
                | (random[9] & 0xff);
        for (int i = 7; i >= 0; i--) {
            buf[i] = ENCODING[(int) (high & 0x1f)];
            high >>>= 5;
        }
        for (int i = 15; i >= 8; i--) {
            buf[i] = ENCODING[(int) (low & 0x1f)];
            low >>>= 5;
        }
        return new String(buf);
    }
}
