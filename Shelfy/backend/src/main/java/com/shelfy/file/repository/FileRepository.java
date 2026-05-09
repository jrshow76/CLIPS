package com.shelfy.file.repository;

import com.shelfy.file.entity.FileEntity;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;

public interface FileRepository extends JpaRepository<FileEntity, Long> {

    /**
     * 업로더별 파일 목록 조회 (미연결 파일 정리 배치용)
     */
    List<FileEntity> findByUploaderId(Long uploaderId);
}
