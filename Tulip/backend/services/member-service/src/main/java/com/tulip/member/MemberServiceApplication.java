package com.tulip.member;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.scheduling.annotation.EnableScheduling;

/**
 * Tulip+ Member Service (Sprint 1-C).
 *
 * <p>회원·회원증·동의 도메인 CRUD 및 변경 이벤트(Outbox) 발행 마이크로서비스.
 * 포트 8103 에서 기동한다.</p>
 *
 * <p>책임은 다음과 같다.
 * <ul>
 *   <li>회원 등록/검색/수정/소프트삭제 (RLS 격리)</li>
 *   <li>회원증 발급/갱신/정지</li>
 *   <li>개인정보 처리 동의 이력</li>
 *   <li>변경 시 {@code mbr_outbox} 적재 → Kafka 발행</li>
 * </ul>
 * </p>
 */
@SpringBootApplication
@EnableScheduling
public class MemberServiceApplication {

    public static void main(String[] args) {
        SpringApplication.run(MemberServiceApplication.class, args);
    }
}
