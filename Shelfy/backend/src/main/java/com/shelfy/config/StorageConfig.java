package com.shelfy.config;

import io.minio.MinioClient;
import org.apache.tika.Tika;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

/**
 * Object Storage 및 파일 처리 관련 Bean 설정
 */
@Configuration
public class StorageConfig {

    @Value("${storage.minio.endpoint}")
    private String endpoint;

    @Value("${storage.minio.access-key}")
    private String accessKey;

    @Value("${storage.minio.secret-key}")
    private String secretKey;

    /**
     * MinIO 클라이언트 Bean
     */
    @Bean
    public MinioClient minioClient() {
        return MinioClient.builder()
                .endpoint(endpoint)
                .credentials(accessKey, secretKey)
                .build();
    }

    /**
     * Apache Tika - Magic Bytes 기반 MIME 타입 감지
     */
    @Bean
    public Tika tika() {
        return new Tika();
    }
}
