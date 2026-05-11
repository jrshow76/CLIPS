package com.tulip.codepolicy;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.cache.annotation.EnableCaching;
import org.springframework.scheduling.annotation.EnableScheduling;

/**
 * Tulip+ Code &amp; Policy Service (Sprint 1-C).
 *
 * <p>코드 마스터(자료유형·언어·통화 등) + 정책(대출/예약/연체/출입/시설) 관리 마이크로서비스.
 * 포트 8104 에서 기동한다.</p>
 *
 * <p>책임:
 * <ul>
 *   <li>코드 그룹/코드 CRUD (글로벌+테넌트)</li>
 *   <li>정책 CRUD + 할당 + 효력 정책 평가</li>
 *   <li>글로벌 코드 Redis 캐시 (시작 시 적재·변경 시 무효화)</li>
 *   <li>변경 시 cd_outbox 적재 → Kafka 발행</li>
 * </ul>
 * </p>
 */
@SpringBootApplication
@EnableScheduling
@EnableCaching
public class CodePolicyServiceApplication {

    public static void main(String[] args) {
        SpringApplication.run(CodePolicyServiceApplication.class, args);
    }
}
