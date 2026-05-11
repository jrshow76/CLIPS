package com.tulip.codepolicy.config;

import org.springframework.boot.context.properties.ConfigurationProperties;

import java.util.ArrayList;
import java.util.List;

/**
 * code-policy-service 설정. {@code tulip.code-policy.*} 로 매핑.
 */
@ConfigurationProperties(prefix = "tulip.code-policy")
public class CodePolicyProperties {

    private final Cache cache = new Cache();
    private final Outbox outbox = new Outbox();

    public Cache getCache() { return cache; }
    public Outbox getOutbox() { return outbox; }

    public static class Cache {
        private long ttlSeconds = 3600L;
        private List<String> preloadGroups = new ArrayList<>();

        public long getTtlSeconds() { return ttlSeconds; }
        public void setTtlSeconds(long ttlSeconds) { this.ttlSeconds = ttlSeconds; }
        public List<String> getPreloadGroups() { return preloadGroups; }
        public void setPreloadGroups(List<String> preloadGroups) { this.preloadGroups = preloadGroups; }
    }

    public static class Outbox {
        private long pollIntervalMs = 1000L;
        private int batchSize = 100;

        public long getPollIntervalMs() { return pollIntervalMs; }
        public void setPollIntervalMs(long pollIntervalMs) { this.pollIntervalMs = pollIntervalMs; }
        public int getBatchSize() { return batchSize; }
        public void setBatchSize(int batchSize) { this.batchSize = batchSize; }
    }
}
