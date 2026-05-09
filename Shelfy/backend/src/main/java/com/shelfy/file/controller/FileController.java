package com.shelfy.file.controller;

import com.shelfy.common.exception.ErrorCode;
import com.shelfy.common.exception.ShelfyException;
import com.shelfy.common.response.ApiResponse;
import com.shelfy.file.dto.response.FileUploadResponse;
import com.shelfy.file.entity.FileEntity;
import com.shelfy.file.service.FileService;
import com.shelfy.security.CustomUserDetails;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MultipartFile;

/**
 * 파일 업로드 API 컨트롤러
 * <p>
 * Base URL: /api/v1/files
 */
@RestController
@RequestMapping("/api/v1/files")
@RequiredArgsConstructor
public class FileController {

    private final FileService fileService;

    /**
     * POST /api/v1/files/upload - 이미지 업로드
     * <p>
     * 요청: multipart/form-data
     * - file: 이미지 파일 (JPG/PNG/WEBP, 최대 10MB)
     * - type: ITEM_IMAGE / PROFILE_IMAGE
     */
    @PostMapping("/upload")
    public ResponseEntity<ApiResponse<FileUploadResponse>> upload(
            @RequestParam("file") MultipartFile file,
            @RequestParam("type") String type,
            @AuthenticationPrincipal CustomUserDetails userDetails) {

        FileEntity.FileType fileType = parseFileType(type);
        FileUploadResponse response = fileService.upload(file, fileType, userDetails.getUserId());

        return ResponseEntity.status(HttpStatus.CREATED)
                .body(ApiResponse.success(response));
    }

    private FileEntity.FileType parseFileType(String type) {
        try {
            return FileEntity.FileType.valueOf(type);
        } catch (IllegalArgumentException e) {
            throw new ShelfyException(ErrorCode.INVALID_INPUT);
        }
    }
}
