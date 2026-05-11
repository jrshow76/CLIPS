package com.tulip.tenant;

import org.mybatis.spring.annotation.MapperScan;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.scheduling.annotation.EnableScheduling;
import org.springframework.transaction.annotation.EnableTransactionManagement;

/**
 * Tulip+ Tenant Service (Sprint 1-C).
 *
 * <p>테넌트·라이브러리·분관·테넌트 설정 마스터 데이터의 단일 소유 서비스.
 * Polling Outbox Publisher 가 도메인 이벤트를 Kafka 로 전파한다.
 * 기본 포트 8102.</p>
 */
@SpringBootApplication
@EnableScheduling
@EnableTransactionManagement
@MapperScan("com.tulip.tenant.infra.mapper")
public class TenantServiceApplication {

    public static void main(String[] args) {
        SpringApplication.run(TenantServiceApplication.class, args);
    }
}
