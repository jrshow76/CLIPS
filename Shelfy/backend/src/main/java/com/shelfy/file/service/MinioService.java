package com.shelfy.file.service;

import com.shelfy.common.exception.ErrorCode;
import com.shelfy.common.exception.ShelfyException;
import io.minio.MinioClient;
import io.minio.PutObjectArgs;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

import java.io.InputStream;

/**
 * MinIO Object Storage 연동 서비스
 * <p>
 * 파일을 서버 로컬에 저장하지 않고 스트림으로 MinIO에 직접 전송한다.
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class MinioService {

    private final MinioClient minioClient;

    @Value("${storage.minio.bucket}")
    private String bucket;

    @Value("${storage.cdn-base-url}")
    private String cdnBaseUrl;

    /**
     * 파일 업로드 후 CDN URL 반환
     *
     * @param objectName 저장될 오브젝트 경로 (e.g. "items/uuid-filename.jpg")
     * @param inputStream 파일 스트림
     * @param contentType MIME 타입
     * @param fileSize 파일 크기 (bytes)
     * @return CDN 접근 URL
     */
    public String upload(String objectName, InputStream inputStream,
            String contentType, long fileSize) {
        try {
            minioClient.putObject(
                    PutObjectArgs.builder()
                            .bucket(bucket)
                            .object(objectName)
                            .stream(inputStream, fileSize, -1)
                            .contentType(contentType)
                            .build()
            );
            String cdnUrl = cdnBaseUrl + "/" + objectName;
            log.debug("File uploaded to MinIO: object={}, url={}", objectName, cdnUrl);
            return cdnUrl;
        } catch (Exception e) {
            log.error("MinIO upload failed: object={}", objectName, e);
            throw new ShelfyException(ErrorCode.INTERNAL_SERVER_ERROR);
        }
    }

    /**
     * 오브젝트 삭제
     */
    public void delete(String objectName) {
        try {
            minioClient.removeObject(
                    io.minio.RemoveObjectArgs.builder()
                            .bucket(bucket)
                            .object(objectName)
                            .build()
            );
            log.debug("File deleted from MinIO: object={}", objectName);
        } catch (Exception e) {
            log.error("MinIO delete failed: object={}", objectName, e);
            throw new ShelfyException(ErrorCode.INTERNAL_SERVER_ERROR);
        }
    }
}
