package com.tulip.member.config;

import org.springframework.boot.context.properties.ConfigurationProperties;

/**
 * member-service 의 application 설정을 매핑하는 properties 빈.
 *
 * <p>application.yml 의 {@code tulip.member.*} 경로와 매핑된다.</p>
 */
@ConfigurationProperties(prefix = "tulip.member")
public class MemberProperties {

    private String piiPassphrase;
    private int softDeleteGraceDays = 30;
    private final Outbox outbox = new Outbox();

    public String getPiiPassphrase() { return piiPassphrase; }
    public void setPiiPassphrase(String piiPassphrase) { this.piiPassphrase = piiPassphrase; }
    public int getSoftDeleteGraceDays() { return softDeleteGraceDays; }
    public void setSoftDeleteGraceDays(int softDeleteGraceDays) { this.softDeleteGraceDays = softDeleteGraceDays; }
    public Outbox getOutbox() { return outbox; }

    /** Outbox 폴링 설정. */
    public static class Outbox {
        private long pollIntervalMs = 1000L;
        private int batchSize = 100;

        public long getPollIntervalMs() { return pollIntervalMs; }
        public void setPollIntervalMs(long pollIntervalMs) { this.pollIntervalMs = pollIntervalMs; }
        public int getBatchSize() { return batchSize; }
        public void setBatchSize(int batchSize) { this.batchSize = batchSize; }
    }
}
