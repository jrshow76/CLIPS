package com.shelfy.file.dto.response;

import lombok.AllArgsConstructor;
import lombok.Getter;
import lombok.NoArgsConstructor;

import java.time.Instant;

@Getter
@NoArgsConstructor
@AllArgsConstructor
public class FileUploadResponse {

    private Long imageId;
    private String url;
    private String fileName;
    private long fileSize;
    private String uploadedAt;

    public static Builder builder() {
        return new Builder();
    }

    public static class Builder {
        private Long imageId;
        private String url;
        private String fileName;
        private long fileSize;

        public Builder imageId(Long imageId) { this.imageId = imageId; return this; }
        public Builder url(String url) { this.url = url; return this; }
        public Builder fileName(String fileName) { this.fileName = fileName; return this; }
        public Builder fileSize(long fileSize) { this.fileSize = fileSize; return this; }

        public FileUploadResponse build() {
            return new FileUploadResponse(imageId, url, fileName, fileSize, Instant.now().toString());
        }
    }
}
