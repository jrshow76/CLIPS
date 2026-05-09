'use client'

/**
 * ProfileForm - 닉네임, 소개, 프로필 이미지 수정 폼
 * 마이페이지 > 내 정보 수정 탭에서 사용
 */

import { useState, useRef } from 'react'
import { Button } from '@/components/common/Button'
import { useToast } from '@/components/common/Toast'
import { useMyProfile, useUpdateProfile } from '@/hooks/useProfile'
import { useAuth } from '@/hooks/useAuth'
import { uploadFile } from '@/lib/api/files'

export function ProfileForm() {
  const toast = useToast()
  const { updateUser } = useAuth()
  const { data: profile, isLoading } = useMyProfile()
  const updateProfile = useUpdateProfile()

  const [nickname, setNickname] = useState('')
  const [bio, setBio] = useState('')
  const [profileImagePreview, setProfileImagePreview] = useState<string | null>(null)
  const [uploadedImageId, setUploadedImageId] = useState<string | null>(null)
  const [imageUploading, setImageUploading] = useState(false)
  const [errors, setErrors] = useState<Record<string, string>>({})
  const fileInputRef = useRef<HTMLInputElement>(null)

  // 프로필 데이터 로드 후 폼 초기화
  const [initialized, setInitialized] = useState(false)
  if (profile && !initialized) {
    setNickname(profile.nickname ?? '')
    setBio(profile.bio ?? '')
    setInitialized(true)
  }

  const handleImageChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return

    if (!['image/jpeg', 'image/png', 'image/webp'].includes(file.type)) {
      toast.error('JPG, PNG, WEBP 형식의 이미지만 업로드할 수 있습니다.')
      return
    }
    if (file.size > 5 * 1024 * 1024) {
      toast.error('프로필 이미지는 5MB 이하만 업로드할 수 있습니다.')
      return
    }

    const previewUrl = URL.createObjectURL(file)
    setProfileImagePreview(previewUrl)
    setImageUploading(true)

    try {
      const uploaded = await uploadFile(file, 'PROFILE_IMAGE')
      setUploadedImageId(uploaded.imageId)
    } catch {
      toast.error('이미지 업로드에 실패했습니다.')
      setProfileImagePreview(null)
    } finally {
      setImageUploading(false)
    }

    e.target.value = ''
  }

  const validate = (): boolean => {
    const newErrors: Record<string, string> = {}
    if (!nickname.trim()) {
      newErrors.nickname = '닉네임을 입력해주세요.'
    } else if (nickname.trim().length < 2) {
      newErrors.nickname = '닉네임은 2자 이상이어야 합니다.'
    } else if (nickname.trim().length > 20) {
      newErrors.nickname = '닉네임은 20자 이하이어야 합니다.'
    }
    if (bio.length > 200) {
      newErrors.bio = '소개는 200자 이하이어야 합니다.'
    }
    setErrors(newErrors)
    return Object.keys(newErrors).length === 0
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!validate()) return

    try {
      const updated = await updateProfile.mutateAsync({
        nickname: nickname.trim(),
        bio: bio.trim() || undefined,
        profileImageId: uploadedImageId ?? undefined,
      })
      // 전역 Auth 상태의 닉네임도 업데이트
      updateUser({
        userId: updated.userId,
        email: updated.email,
        nickname: updated.nickname,
        emailVerified: updated.emailVerified,
        profileImageUrl: updated.profileImageUrl,
      })
      toast.success('프로필이 수정되었습니다.')
    } catch (err: any) {
      toast.error(err?.message ?? '프로필 수정에 실패했습니다.')
    }
  }

  if (isLoading) {
    return (
      <div
        style={{
          padding: 'var(--space-12)',
          textAlign: 'center',
          color: 'var(--color-text-tertiary)',
        }}
      >
        프로필 정보를 불러오는 중...
      </div>
    )
  }

  const avatarDisplay = profileImagePreview ?? profile?.profileImageUrl
  const avatarInitial = (profile?.nickname ?? 'U')[0].toUpperCase()

  return (
    <form onSubmit={handleSubmit} noValidate>
      {/* 프로필 이미지 */}
      <div
        className="form-field"
        style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-6)', marginBottom: 'var(--space-8)' }}
      >
        <div style={{ position: 'relative', flexShrink: 0 }}>
          <div
            className="profile-hero__avatar"
            style={{ width: 80, height: 80, fontSize: 'var(--font-size-2xl)' }}
            aria-label={`${profile?.nickname ?? ''} 프로필 이미지`}
          >
            {avatarDisplay ? (
              // eslint-disable-next-line @next/next/no-img-element
              <img
                src={avatarDisplay}
                alt="프로필 이미지"
                style={{
                  width: '100%',
                  height: '100%',
                  objectFit: 'cover',
                  borderRadius: '50%',
                  opacity: imageUploading ? 0.5 : 1,
                }}
              />
            ) : (
              avatarInitial
            )}
          </div>
          <button
            type="button"
            className="profile-hero__avatar-edit-btn"
            aria-label="프로필 이미지 변경"
            onClick={() => fileInputRef.current?.click()}
            disabled={imageUploading}
          >
            <svg
              width="12"
              height="12"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2.5"
              aria-hidden="true"
            >
              <path d="M11 4H4a2 2 0 00-2 2v14a2 2 0 002 2h14a2 2 0 002-2v-7" />
              <path d="M18.5 2.5a2.121 2.121 0 013 3L12 15l-4 1 1-4 9.5-9.5z" />
            </svg>
          </button>
        </div>
        <div>
          <button
            type="button"
            className="btn btn--secondary btn--sm"
            onClick={() => fileInputRef.current?.click()}
            disabled={imageUploading}
          >
            {imageUploading ? '업로드 중...' : '이미지 변경'}
          </button>
          <p
            className="form-hint"
            style={{ marginTop: 'var(--space-2)', marginBottom: 0 }}
          >
            JPG, PNG, WEBP · 최대 5MB
          </p>
        </div>
        <input
          ref={fileInputRef}
          type="file"
          accept="image/jpeg,image/png,image/webp"
          aria-hidden="true"
          style={{ display: 'none' }}
          onChange={handleImageChange}
        />
      </div>

      {/* 닉네임 */}
      <div className="form-field">
        <label className="form-label form-label--required" htmlFor="profile-nickname">
          닉네임
        </label>
        <input
          type="text"
          id="profile-nickname"
          className={`form-input ${errors.nickname ? 'form-input--error' : ''}`}
          value={nickname}
          maxLength={20}
          onChange={(e) => setNickname(e.target.value)}
          placeholder="닉네임을 입력하세요"
          aria-invalid={!!errors.nickname}
          aria-describedby={errors.nickname ? 'nickname-error' : 'nickname-hint'}
        />
        {errors.nickname ? (
          <p className="form-error" id="nickname-error" role="alert">
            {errors.nickname}
          </p>
        ) : (
          <p className="form-hint" id="nickname-hint">
            2~20자 이내, 영문/한글/숫자 사용 가능
          </p>
        )}
      </div>

      {/* 소개 */}
      <div className="form-field" style={{ marginTop: 'var(--space-5)' }}>
        <label className="form-label" htmlFor="profile-bio">
          소개
        </label>
        <textarea
          id="profile-bio"
          className={`form-textarea ${errors.bio ? 'form-textarea--error' : ''}`}
          value={bio}
          maxLength={200}
          rows={4}
          onChange={(e) => setBio(e.target.value)}
          placeholder="자신을 소개해주세요 (선택)"
          aria-invalid={!!errors.bio}
        />
        <div
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
          }}
        >
          {errors.bio ? (
            <p className="form-error" role="alert">
              {errors.bio}
            </p>
          ) : (
            <span />
          )}
          <span
            className="form-counter"
            style={{ marginLeft: 'auto' }}
            aria-live="polite"
          >
            {bio.length} / 200
          </span>
        </div>
      </div>

      {/* 이메일 (읽기 전용) */}
      <div className="form-field" style={{ marginTop: 'var(--space-5)' }}>
        <label className="form-label" htmlFor="profile-email">
          이메일
        </label>
        <input
          type="email"
          id="profile-email"
          className="form-input"
          value={profile?.email ?? ''}
          readOnly
          style={{ backgroundColor: 'var(--color-bg-muted)', cursor: 'not-allowed' }}
          aria-readonly="true"
        />
        <p className="form-hint">이메일은 변경할 수 없습니다.</p>
      </div>

      <div style={{ marginTop: 'var(--space-8)', display: 'flex', justifyContent: 'flex-end' }}>
        <Button
          type="submit"
          variant="primary"
          loading={updateProfile.isPending}
          disabled={imageUploading}
        >
          변경 사항 저장
        </Button>
      </div>
    </form>
  )
}
