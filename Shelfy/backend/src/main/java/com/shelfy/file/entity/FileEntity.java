package com.shelfy.file.entity;

import jakarta.persistence.*;
import lombok.AccessLevel;
import lombok.Builder;
import lombok.Getter;
import lombok.NoArgsConstructor;
import org.hibernate.annotations.CreationTimestamp;

import java.time.LocalDateTime;

/**
 * files 테이블 JPA 엔티티
 * <p>
 * 업로드된 파일의 메타데이터를 관리한다.
 * 실제 파일은 MinIO/Cloud Object Storage에 저장되고 CDN URL을 보관한다.
 */
@Entity
@Table(name = "files")
@Getter
@NoArgsConstructor(access = AccessLevel.PROTECTED)
public class FileEntity {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(nullable = false)
    private Long uploaderId;

    @Enumerated(EnumType.STRING)
    @Column(nullable = false, length = 20)
    private FileType fileType;

    @Column(nullable = false, length = 255)
    private String originalName;

    @Column(nullable = false, length = 255)
    private String storedName;   // UUID 기반 파일명

    @Column(nullable = false, length = 2048)
    private String cdnUrl;

    @Column(nullable = false)
    private Long fileSize;       // bytes

    @Column(nullable = false, length = 100)
    private String mimeType;

    @CreationTimestamp
    @Column(nullable = false, updatable = false)
    private LocalDateTime createdAt;

    @Builder
    public FileEntity(Long uploaderId, FileType fileType,
            String originalName, String storedName, String cdnUrl,
            Long fileSize, String mimeType) {
        this.uploaderId = uploaderId;
        this.fileType = fileType;
        this.originalName = originalName;
        this.storedName = storedName;
        this.cdnUrl = cdnUrl;
        this.fileSize = fileSize;
        this.mimeType = mimeType;
    }

    public enum FileType {
        ITEM_IMAGE,
        PROFILE_IMAGE
    }
}
