package com.shelfy.file.service;

import com.shelfy.common.exception.ErrorCode;
import com.shelfy.common.exception.ShelfyException;
import com.shelfy.file.dto.response.FileUploadResponse;
import com.shelfy.file.entity.FileEntity;
import com.shelfy.file.repository.FileRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.apache.tika.Tika;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.multipart.MultipartFile;

import java.io.IOException;
import java.io.InputStream;
import java.util.Set;
import java.util.UUID;

/**
 * 파일 업로드 비즈니스 로직
 * <p>
 * 보안 정책:
 * - Apache Tika를 사용한 Magic Bytes 기반 MIME 타입 검증 (확장자 스푸핑 방지)
 * - 파일명은 UUID로 생성하여 원본명 노출 방지
 * - 서버 로컬 저장 없이 스트림으로 MinIO 전송
 */
@Slf4j
@Service
@Transactional(readOnly = true)
@RequiredArgsConstructor
public class FileService {

    private static final long MAX_FILE_SIZE_BYTES = 10L * 1024 * 1024; // 10MB
    private static final Set<String> ALLOWED_MIME_TYPES = Set.of(
            "image/jpeg",
            "image/png",
            "image/webp"
    );
    private static final Set<String> ALLOWED_EXTENSIONS = Set.of(".jpg", ".jpeg", ".png", ".webp");

    private final FileRepository fileRepository;
    private final MinioService minioService;
    private final Tika tika;

    /**
     * 이미지 파일 업로드
     * <p>
     * 처리 순서:
     * 1. 파일 크기 검증
     * 2. Magic Bytes로 MIME 타입 검증 (Apache Tika)
     * 3. UUID 기반 저장명 생성
     * 4. MinIO에 스트림 업로드
     * 5. 파일 메타데이터 DB 저장
     *
     * @param file       업로드 파일
     * @param fileType   업로드 타입 (ITEM_IMAGE / PROFILE_IMAGE)
     * @param uploaderId 업로더 사용자 ID
     * @return 업로드 결과 (imageId, url 포함)
     */
    @Transactional
    public FileUploadResponse upload(MultipartFile file, FileEntity.FileType fileType,
            Long uploaderId) {
        validateFile(file);

        String detectedMimeType = detectMimeType(file);
        validateMimeType(detectedMimeType);

        String extension = extractExtension(detectedMimeType);
        String storedName = UUID.randomUUID().toString() + extension;

        // 타입별 경로 분리
        String folder = fileType == FileEntity.FileType.ITEM_IMAGE ? "items" : "profiles";
        String objectName = folder + "/" + storedName;

        String cdnUrl;
        try (InputStream inputStream = file.getInputStream()) {
            cdnUrl = minioService.upload(objectName, inputStream, detectedMimeType, file.getSize());
        } catch (IOException e) {
            log.error("File stream error: {}", e.getMessage());
            throw new ShelfyException(ErrorCode.INTERNAL_SERVER_ERROR);
        }

        FileEntity fileEntity = FileEntity.builder()
                .uploaderId(uploaderId)
                .fileType(fileType)
                .originalName(file.getOriginalFilename())
                .storedName(storedName)
                .cdnUrl(cdnUrl)
                .fileSize(file.getSize())
                .mimeType(detectedMimeType)
                .build();

        FileEntity saved = fileRepository.save(fileEntity);

        log.info("File uploaded: fileId={}, uploaderId={}, size={}", saved.getId(), uploaderId, file.getSize());

        return FileUploadResponse.builder()
                .imageId(saved.getId())
                .url(cdnUrl)
                .fileName(file.getOriginalFilename())
                .fileSize(file.getSize())
                .build();
    }

    // ===== 검증 메서드 =====

    private void validateFile(MultipartFile file) {
        if (file == null || file.isEmpty()) {
            throw new ShelfyException(ErrorCode.INVALID_INPUT);
        }
        if (file.getSize() > MAX_FILE_SIZE_BYTES) {
            throw new ShelfyException(ErrorCode.FILE_SIZE_EXCEEDED);
        }
    }

    /**
     * Apache Tika로 Magic Bytes 기반 MIME 타입 감지
     * Content-Type 헤더나 확장자는 신뢰하지 않는다.
     */
    private String detectMimeType(MultipartFile file) {
        try {
            return tika.detect(file.getInputStream());
        } catch (IOException e) {
            log.error("MIME type detection failed: {}", e.getMessage());
            throw new ShelfyException(ErrorCode.UNSUPPORTED_FILE_TYPE);
        }
    }

    private void validateMimeType(String mimeType) {
        if (!ALLOWED_MIME_TYPES.contains(mimeType)) {
            throw new ShelfyException(ErrorCode.UNSUPPORTED_FILE_TYPE);
        }
    }

    /**
     * MIME 타입으로 파일 확장자 결정
     */
    private String extractExtension(String mimeType) {
        return switch (mimeType) {
            case "image/jpeg" -> ".jpg";
            case "image/png" -> ".png";
            case "image/webp" -> ".webp";
            default -> throw new ShelfyException(ErrorCode.UNSUPPORTED_FILE_TYPE);
        };
    }
}
