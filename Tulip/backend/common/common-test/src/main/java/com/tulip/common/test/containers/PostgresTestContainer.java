package com.tulip.common.test.containers;

import org.testcontainers.containers.PostgreSQLContainer;
import org.testcontainers.utility.DockerImageName;

/**
 * 통합 테스트용 PostgreSQL Testcontainer 헬퍼.
 *
 * <p>각 테스트 클래스에서 {@code @Container static PostgreSQLContainer<?> PG = PostgresTestContainer.singleton();}
 * 형태로 사용한다. 동일 이미지를 재사용하여 테스트 시간을 단축한다.</p>
 */
public final class PostgresTestContainer {

    private static final DockerImageName IMAGE = DockerImageName.parse("postgres:15-alpine");

    private static volatile PostgreSQLContainer<?> SHARED;

    private PostgresTestContainer() {
    }

    /** 공유 컨테이너를 lazy 로 반환한다. JVM 종료까지 재사용. */
    public static PostgreSQLContainer<?> singleton() {
        PostgreSQLContainer<?> local = SHARED;
        if (local == null) {
            synchronized (PostgresTestContainer.class) {
                local = SHARED;
                if (local == null) {
                    local = new PostgreSQLContainer<>(IMAGE)
                            .withDatabaseName("tulip")
                            .withUsername("tulip")
                            .withPassword("tulip")
                            .withReuse(true);
                    local.start();
                    SHARED = local;
                }
            }
        }
        return local;
    }
}
