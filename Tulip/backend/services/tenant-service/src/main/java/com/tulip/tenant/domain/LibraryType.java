package com.tulip.tenant.domain;

/**
 * 라이브러리 유형. CENTRAL=중앙관, BRANCH=분관, INTEGRATED=통합.
 */
public enum LibraryType {
    CENTRAL,
    BRANCH,
    INTEGRATED;

    public static LibraryType parseOrDefault(String value, LibraryType fallback) {
        if (value == null) {
            return fallback;
        }
        try {
            return LibraryType.valueOf(value.toUpperCase());
        } catch (IllegalArgumentException e) {
            return fallback;
        }
    }
}
