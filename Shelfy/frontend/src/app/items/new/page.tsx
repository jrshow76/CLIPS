'use client'

/**
 * SCR-022 상품 등록 페이지 (4단계 멀티 스텝 폼)
 * Designer 05_item-register.html 구조 기반
 */

import { useState, useCallback, useRef, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { Button } from '@/components/common/Button'
import { useToast } from '@/components/common/Toast'
import { useCreateItem } from '@/hooks/useItems'
import { useAuth } from '@/hooks/useAuth'
import { uploadFile } from '@/lib/api/files'
import type {
  SaleType,
  ItemCategory,
  ItemStatus,
  SubscriptionPlanRequest,
  SubscriptionPeriod,
} from '@/types/item'

/* --------------------------------------------------------------------------
   타입 정의
   -------------------------------------------------------------------------- */
interface PlanDraft {
  id: string
  planName: string
  period: SubscriptionPeriod
  planPrice: number
  description: string
}

interface ImagePreview {
  file: File
  previewUrl: string
  imageId?: string
  uploading: boolean
}

interface FormData {
  title: string
  category: ItemCategory | ''
  description: string
  saleType: SaleType | ''
  price: number | ''
  plans: PlanDraft[]
  images: ImagePreview[]
  thumbnailIndex: number
  tags: string[]
  status: ItemStatus
}

const CATEGORIES: { value: ItemCategory; label: string }[] = [
  { value: 'TEMPLATE', label: '템플릿' },
  { value: 'FONT', label: '폰트' },
  { value: 'ICON', label: '아이콘' },
  { value: 'PHOTO', label: '사진' },
  { value: 'ILLUSTRATION', label: '일러스트' },
  { value: 'VIDEO', label: '비디오' },
  { value: 'MUSIC', label: '음악' },
  { value: 'DOCUMENT', label: '문서' },
  { value: 'CODE', label: '코드' },
  { value: 'OTHER', label: '기타' },
]

const INITIAL_FORM: FormData = {
  title: '',
  category: '',
  description: '',
  saleType: '',
  price: '',
  plans: [],
  images: [],
  thumbnailIndex: 0,
  tags: [],
  status: 'DRAFT',
}

function makePlanId() {
  return `plan-${Date.now()}-${Math.random().toString(36).slice(2)}`
}

/* --------------------------------------------------------------------------
   Step Indicator 컴포넌트
   -------------------------------------------------------------------------- */
const STEP_LABELS = ['기본 정보', '판매 유형', '이미지/태그', '공개 설정']

function StepIndicator({ currentStep }: { currentStep: number }) {
  return (
    <div className="step-indicator" role="list" aria-label="등록 단계">
      {STEP_LABELS.map((label, idx) => {
        const stepNum = idx + 1
        const isCompleted = stepNum < currentStep
        const isActive = stepNum === currentStep

        return (
          <div key={stepNum} style={{ display: 'contents' }}>
            <div
              className={`step ${isCompleted ? 'step--completed' : ''} ${isActive ? 'step--active' : ''}`}
              role="listitem"
              aria-current={isActive ? 'step' : undefined}
            >
              <div
                className="step__circle"
                aria-label={`${stepNum}단계 ${isCompleted ? '완료' : isActive ? '진행중' : '미완료'}`}
              >
                {isCompleted ? (
                  <svg
                    width="14"
                    height="14"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="3"
                    aria-hidden="true"
                  >
                    <polyline points="20 6 9 17 4 12" />
                  </svg>
                ) : (
                  stepNum
                )}
              </div>
              <span className="step__label">{label}</span>
            </div>
            {idx < STEP_LABELS.length - 1 && (
              <div
                className={`step-connector ${isCompleted ? 'step-connector--done' : ''}`}
                aria-hidden="true"
              />
            )}
          </div>
        )
      })}
    </div>
  )
}

/* --------------------------------------------------------------------------
   FormCard Header 컴포넌트
   -------------------------------------------------------------------------- */
function FormCardHeader({
  stepNum,
  title,
  desc,
}: {
  stepNum: number
  title: string
  desc?: string
}) {
  return (
    <div className="form-card__header">
      <span className="form-card__step-num" aria-hidden="true">
        {stepNum}
      </span>
      <span className="form-card__title">{title}</span>
      {desc && (
        <span className="form-card__desc" aria-hidden="true">
          {desc}
        </span>
      )}
    </div>
  )
}

/* --------------------------------------------------------------------------
   Step 1: 기본 정보
   -------------------------------------------------------------------------- */
interface Step1Props {
  form: FormData
  onChange: (patch: Partial<FormData>) => void
  errors: Record<string, string>
}

function Step1BasicInfo({ form, onChange, errors }: Step1Props) {
  return (
    <div className="form-card__body">
      <div className="form-field">
        <label className="form-label form-label--required" htmlFor="title">
          상품 제목
        </label>
        <input
          type="text"
          id="title"
          className={`form-input ${errors.title ? 'form-input--error' : ''}`}
          placeholder="상품 제목을 입력하세요 (최대 100자)"
          value={form.title}
          maxLength={100}
          onChange={(e) => onChange({ title: e.target.value })}
          aria-describedby={errors.title ? 'title-error' : undefined}
          aria-invalid={!!errors.title}
        />
        {errors.title && (
          <p className="form-error" id="title-error" role="alert">
            {errors.title}
          </p>
        )}
      </div>

      <div className="form-row form-row--2col" style={{ marginTop: 'var(--space-5)' }}>
        <div className="form-field">
          <label className="form-label form-label--required" htmlFor="category">
            카테고리
          </label>
          <select
            id="category"
            className={`form-select ${errors.category ? 'form-select--error' : ''}`}
            value={form.category}
            onChange={(e) => onChange({ category: e.target.value as ItemCategory })}
            aria-describedby={errors.category ? 'category-error' : undefined}
            aria-invalid={!!errors.category}
          >
            <option value="">카테고리 선택</option>
            {CATEGORIES.map((c) => (
              <option key={c.value} value={c.value}>
                {c.label}
              </option>
            ))}
          </select>
          {errors.category && (
            <p className="form-error" id="category-error" role="alert">
              {errors.category}
            </p>
          )}
        </div>
      </div>

      <div className="form-field" style={{ marginTop: 'var(--space-5)' }}>
        <label className="form-label form-label--required" htmlFor="description">
          상품 설명
        </label>
        <textarea
          id="description"
          className={`form-textarea form-textarea--grow ${errors.description ? 'form-textarea--error' : ''}`}
          placeholder="상품에 대한 상세 설명을 입력하세요"
          value={form.description}
          maxLength={5000}
          onChange={(e) => onChange({ description: e.target.value })}
          aria-describedby={errors.description ? 'description-error' : 'description-hint'}
          aria-invalid={!!errors.description}
        />
        <p className="form-hint" id="description-hint">
          구매자가 상품을 이해하는 데 도움이 되는 상세 정보를 입력해주세요.
        </p>
        {errors.description && (
          <p className="form-error" id="description-error" role="alert">
            {errors.description}
          </p>
        )}
      </div>
    </div>
  )
}

/* --------------------------------------------------------------------------
   Step 2: 판매 유형 및 가격
   -------------------------------------------------------------------------- */
interface Step2Props {
  form: FormData
  onChange: (patch: Partial<FormData>) => void
  errors: Record<string, string>
}

function Step2SaleType({ form, onChange, errors }: Step2Props) {
  const addPlan = () => {
    const newPlan: PlanDraft = {
      id: makePlanId(),
      planName: '',
      period: 'MONTHLY',
      planPrice: 0,
      description: '',
    }
    onChange({ plans: [...form.plans, newPlan] })
  }

  const removePlan = (id: string) => {
    onChange({ plans: form.plans.filter((p) => p.id !== id) })
  }

  const updatePlan = (id: string, patch: Partial<PlanDraft>) => {
    onChange({
      plans: form.plans.map((p) => (p.id === id ? { ...p, ...patch } : p)),
    })
  }

  const showPurchasePrice = form.saleType === 'PURCHASE' || form.saleType === 'BOTH'
  const showPlans = form.saleType === 'SUBSCRIBE' || form.saleType === 'BOTH'

  return (
    <div className="form-card__body">
      {/* 판매 방식 선택 */}
      <fieldset style={{ border: 'none', padding: 0, marginBottom: 'var(--space-8)' }}>
        <legend
          style={{
            fontSize: 'var(--font-size-sm)',
            fontWeight: 'var(--font-weight-semibold)',
            color: 'var(--color-text-primary)',
            marginBottom: 'var(--space-4)',
          }}
        >
          판매 방식 선택{' '}
          <span style={{ color: 'var(--color-error)' }} aria-hidden="true">
            *
          </span>
          <span className="sr-only">(필수)</span>
        </legend>

        {errors.saleType && (
          <p className="form-error" role="alert" style={{ marginBottom: 'var(--space-3)' }}>
            {errors.saleType}
          </p>
        )}

        <div className="sale-type-cards" role="radiogroup" aria-required="true">
          {(
            [
              {
                value: 'PURCHASE' as SaleType,
                icon: '🛒',
                title: '단일 구매',
                desc: '고객이 한 번 결제하고 영구적으로 사용합니다.',
              },
              {
                value: 'SUBSCRIBE' as SaleType,
                icon: '🔄',
                title: '구독',
                desc: '정기 결제로 지속적인 수익을 만들어보세요.',
              },
              {
                value: 'BOTH' as SaleType,
                icon: '✨',
                title: '구매 + 구독',
                desc: '단일 구매와 구독 모두 제공합니다.',
              },
            ] as const
          ).map(({ value, icon, title, desc }) => {
            const selected = form.saleType === value
            const descId = `sale-type-desc-${value.toLowerCase()}`
            return (
              <label
                key={value}
                className={`sale-type-card ${selected ? 'sale-type-card--selected' : ''}`}
                aria-label={`${title}${selected ? ' (현재 선택됨)' : ''}`}
              >
                <input
                  type="radio"
                  name="saleType"
                  value={value}
                  checked={selected}
                  onChange={() => onChange({ saleType: value })}
                  aria-describedby={descId}
                />
                <div className="sale-type-card__selected-mark" aria-hidden="true" />
                <div className="sale-type-card__icon" aria-hidden="true">
                  {icon}
                </div>
                <div className="sale-type-card__title">{title}</div>
                <div className="sale-type-card__desc" id={descId}>
                  {desc}
                </div>
              </label>
            )
          })}
        </div>
      </fieldset>

      {/* 단일 구매 가격 입력 */}
      {showPurchasePrice && (
        <div className="pricing-section" style={{ marginBottom: 'var(--space-5)' }}>
          <div className="pricing-section__header">단일 구매 가격</div>
          <div className="pricing-section__body">
            <div className="form-field">
              <label className="form-label form-label--required" htmlFor="price">
                판매 가격
              </label>
              <div className="price-input-wrap">
                <span className="price-input-wrap__symbol" aria-hidden="true">
                  ₩
                </span>
                <input
                  type="number"
                  id="price"
                  className={`form-input ${errors.price ? 'form-input--error' : ''}`}
                  placeholder="0"
                  min={100}
                  value={form.price}
                  onChange={(e) =>
                    onChange({ price: e.target.value === '' ? '' : Number(e.target.value) })
                  }
                  aria-label="판매 가격 (원)"
                  aria-describedby={errors.price ? 'price-error' : undefined}
                  aria-invalid={!!errors.price}
                />
              </div>
              {errors.price && (
                <p className="form-error" id="price-error" role="alert">
                  {errors.price}
                </p>
              )}
            </div>
          </div>
        </div>
      )}

      {/* 구독 플랜 설정 */}
      {showPlans && (
        <div className="pricing-section">
          <div className="pricing-section__header">
            구독 플랜 설정
            <span
              style={{
                fontSize: 'var(--font-size-xs)',
                color: 'var(--color-text-tertiary)',
                fontWeight: 400,
                marginLeft: 'var(--space-2)',
              }}
            >
              최소 1개 이상 등록 필요
            </span>
          </div>
          <div className="pricing-section__body">
            {errors.plans && (
              <p className="form-error" role="alert" style={{ marginBottom: 'var(--space-3)' }}>
                {errors.plans}
              </p>
            )}

            <div className="plan-list" role="list" aria-label="구독 플랜 목록">
              {form.plans.map((plan, idx) => (
                <div key={plan.id} className="plan-item" role="listitem">
                  <div className="plan-item__header">
                    <span className="plan-item__title">플랜 {idx + 1}</span>
                    <button
                      type="button"
                      className="plan-item__remove"
                      aria-label={`플랜 ${idx + 1} 삭제`}
                      onClick={() => removePlan(plan.id)}
                    >
                      <svg
                        width="14"
                        height="14"
                        viewBox="0 0 24 24"
                        fill="none"
                        stroke="currentColor"
                        strokeWidth="2"
                        aria-hidden="true"
                      >
                        <polyline points="3 6 5 6 21 6" />
                        <path d="M19 6l-1 14a2 2 0 01-2 2H8a2 2 0 01-2-2L5 6" />
                      </svg>
                    </button>
                  </div>

                  <div className="plan-item__fields">
                    <div className="form-field">
                      <label
                        className="form-label form-label--required"
                        htmlFor={`plan-name-${plan.id}`}
                      >
                        플랜 이름
                      </label>
                      <input
                        type="text"
                        id={`plan-name-${plan.id}`}
                        className="form-input"
                        placeholder="예: Basic"
                        value={plan.planName}
                        maxLength={50}
                        onChange={(e) =>
                          updatePlan(plan.id, { planName: e.target.value })
                        }
                      />
                    </div>

                    <div className="form-field">
                      <label
                        className="form-label form-label--required"
                        htmlFor={`plan-period-${plan.id}`}
                      >
                        결제 주기
                      </label>
                      <select
                        id={`plan-period-${plan.id}`}
                        className="form-select"
                        value={plan.period}
                        onChange={(e) =>
                          updatePlan(plan.id, {
                            period: e.target.value as SubscriptionPeriod,
                          })
                        }
                      >
                        <option value="MONTHLY">월간 (MONTHLY)</option>
                        <option value="YEARLY">연간 (YEARLY)</option>
                      </select>
                    </div>

                    <div className="form-field">
                      <label
                        className="form-label form-label--required"
                        htmlFor={`plan-price-${plan.id}`}
                      >
                        플랜 가격
                      </label>
                      <div className="price-input-wrap">
                        <span className="price-input-wrap__symbol" aria-hidden="true">
                          ₩
                        </span>
                        <input
                          type="number"
                          id={`plan-price-${plan.id}`}
                          className="form-input"
                          placeholder="0"
                          min={100}
                          value={plan.planPrice || ''}
                          onChange={(e) =>
                            updatePlan(plan.id, {
                              planPrice: Number(e.target.value),
                            })
                          }
                          aria-label={`플랜 ${idx + 1} 가격 (원)`}
                        />
                      </div>
                    </div>
                  </div>

                  <div className="form-field" style={{ marginTop: 'var(--space-3)' }}>
                    <label className="form-label" htmlFor={`plan-desc-${plan.id}`}>
                      플랜 설명 (선택)
                    </label>
                    <input
                      type="text"
                      id={`plan-desc-${plan.id}`}
                      className="form-input"
                      placeholder="이 플랜에 포함된 혜택을 입력하세요"
                      value={plan.description}
                      maxLength={500}
                      onChange={(e) =>
                        updatePlan(plan.id, { description: e.target.value })
                      }
                    />
                  </div>
                </div>
              ))}
            </div>

            <button type="button" className="add-plan-btn" onClick={addPlan}>
              <svg
                width="16"
                height="16"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2.5"
                aria-hidden="true"
              >
                <line x1="12" y1="5" x2="12" y2="19" />
                <line x1="5" y1="12" x2="19" y2="12" />
              </svg>
              플랜 추가
            </button>
          </div>
        </div>
      )}
    </div>
  )
}

/* --------------------------------------------------------------------------
   Step 3: 이미지 업로드 및 태그
   -------------------------------------------------------------------------- */
interface Step3Props {
  form: FormData
  onChange: (patch: Partial<FormData>) => void
  errors: Record<string, string>
}

function Step3Images({ form, onChange, errors }: Step3Props) {
  const dragOverRef = useRef(false)
  const [isDragOver, setIsDragOver] = useState(false)
  const [tagInput, setTagInput] = useState('')
  const fileInputRef = useRef<HTMLInputElement>(null)
  const currentImagesRef = useRef<ImagePreview[]>(form.images)
  currentImagesRef.current = form.images

  const handleFiles = async (files: FileList) => {
    const remaining = 10 - currentImagesRef.current.length
    if (remaining <= 0) return

    const newFiles = Array.from(files).slice(0, remaining).filter((f) => {
      const validTypes = ['image/jpeg', 'image/png', 'image/webp']
      return validTypes.includes(f.type) && f.size <= 10 * 1024 * 1024
    })

    const previews: ImagePreview[] = newFiles.map((file) => ({
      file,
      previewUrl: URL.createObjectURL(file),
      uploading: true,
    }))

    const withPreviews = [...currentImagesRef.current, ...previews]
    currentImagesRef.current = withPreviews
    onChange({ images: withPreviews })

    for (const preview of previews) {
      try {
        const uploaded = await uploadFile(preview.file, 'ITEM_IMAGE')
        const updated = currentImagesRef.current.map((img: ImagePreview) =>
          img.previewUrl === preview.previewUrl
            ? { ...img, imageId: uploaded.imageId, uploading: false }
            : img
        )
        currentImagesRef.current = updated
        onChange({ images: updated })
      } catch {
        const filtered = currentImagesRef.current.filter(
          (img: ImagePreview) => img.previewUrl !== preview.previewUrl
        )
        currentImagesRef.current = filtered
        onChange({ images: filtered })
      }
    }
  }

  const removeImage = (index: number) => {
    const updated = form.images.filter((_, i) => i !== index)
    const newThumb =
      form.thumbnailIndex >= updated.length
        ? Math.max(0, updated.length - 1)
        : form.thumbnailIndex
    onChange({ images: updated, thumbnailIndex: newThumb })
  }

  const setThumbnail = (index: number) => {
    onChange({ thumbnailIndex: index })
  }

  const addTag = () => {
    const trimmed = tagInput.trim()
    if (!trimmed || form.tags.includes(trimmed) || form.tags.length >= 10) return
    onChange({ tags: [...form.tags, trimmed] })
    setTagInput('')
  }

  const removeTag = (tag: string) => {
    onChange({ tags: form.tags.filter((t) => t !== tag) })
  }

  return (
    <div className="form-card__body">
      {/* 이미지 업로드 영역 */}
      <div className="form-field">
        <span className="form-label form-label--required" id="image-upload-label">
          상품 이미지
        </span>
        {errors.images && (
          <p className="form-error" role="alert" style={{ marginBottom: 'var(--space-2)' }}>
            {errors.images}
          </p>
        )}

        <div
          className={`image-upload-zone ${isDragOver ? 'image-upload-zone--dragover' : ''}`}
          role="button"
          tabIndex={0}
          aria-labelledby="image-upload-label"
          aria-describedby="image-upload-desc"
          onClick={() => fileInputRef.current?.click()}
          onKeyDown={(e) => {
            if (e.key === 'Enter' || e.key === ' ') fileInputRef.current?.click()
          }}
          onDragOver={(e) => {
            e.preventDefault()
            if (!dragOverRef.current) {
              dragOverRef.current = true
              setIsDragOver(true)
            }
          }}
          onDragLeave={() => {
            dragOverRef.current = false
            setIsDragOver(false)
          }}
          onDrop={(e) => {
            e.preventDefault()
            dragOverRef.current = false
            setIsDragOver(false)
            if (e.dataTransfer.files.length > 0) {
              handleFiles(e.dataTransfer.files)
            }
          }}
        >
          <input
            ref={fileInputRef}
            type="file"
            className="image-upload-zone__input"
            accept="image/jpeg,image/png,image/webp"
            multiple
            aria-hidden="true"
            tabIndex={-1}
            onChange={(e) => {
              if (e.target.files) handleFiles(e.target.files)
              e.target.value = ''
            }}
          />
          <div className="image-upload-zone__icon" aria-hidden="true">
            📷
          </div>
          <div className="image-upload-zone__title">
            클릭하거나 파일을 드래그하여 업로드
          </div>
          <div className="image-upload-zone__desc" id="image-upload-desc">
            <strong>JPG, PNG, WEBP</strong> 지원
            <br />
            이미지 1장당 최대 10MB · 최대 10장
          </div>
          <div className="image-upload-zone__limit">
            첫 번째 이미지가 대표 이미지로 자동 설정됩니다
          </div>
        </div>

        {/* 이미지 미리보기 그리드 */}
        {form.images.length > 0 && (
          <div
            className="image-preview-grid"
            role="list"
            aria-label="업로드된 이미지 목록"
          >
            {form.images.map((img, idx) => {
              const isThumbnail = idx === form.thumbnailIndex
              return (
                <div
                  key={img.previewUrl}
                  className={`image-preview-item ${isThumbnail ? 'image-preview-item--thumbnail' : ''}`}
                  role="listitem"
                  aria-label={`이미지 ${idx + 1}${isThumbnail ? ' (대표 이미지)' : ''}`}
                >
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img
                    src={img.previewUrl}
                    alt={`업로드 이미지 ${idx + 1}`}
                    className="image-preview-item__img"
                    style={{ opacity: img.uploading ? 0.5 : 1 }}
                  />
                  {img.uploading && (
                    <div
                      style={{
                        position: 'absolute',
                        inset: 0,
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        background: 'rgba(255,255,255,0.6)',
                        fontSize: '0.75rem',
                        color: 'var(--color-text-tertiary)',
                      }}
                    >
                      업로드 중...
                    </div>
                  )}
                  <div className="image-preview-item__actions">
                    <button
                      type="button"
                      className="image-preview-item__action-btn"
                      aria-label={`이미지 ${idx + 1} 삭제`}
                      onClick={() => removeImage(idx)}
                    >
                      <svg
                        width="10"
                        height="10"
                        viewBox="0 0 24 24"
                        fill="none"
                        stroke="currentColor"
                        strokeWidth="2.5"
                        aria-hidden="true"
                      >
                        <line x1="18" y1="6" x2="6" y2="18" />
                        <line x1="6" y1="6" x2="18" y2="18" />
                      </svg>
                    </button>
                    {!isThumbnail && (
                      <button
                        type="button"
                        className="image-preview-item__action-btn"
                        aria-label={`이미지 ${idx + 1}을 대표 이미지로 설정`}
                        onClick={() => setThumbnail(idx)}
                        title="대표 이미지로 설정"
                      >
                        <svg
                          width="10"
                          height="10"
                          viewBox="0 0 24 24"
                          fill="none"
                          stroke="currentColor"
                          strokeWidth="2.5"
                          aria-hidden="true"
                        >
                          <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2" />
                        </svg>
                      </button>
                    )}
                  </div>
                  {isThumbnail && (
                    <span className="image-preview-item__thumb-badge">대표</span>
                  )}
                </div>
              )
            })}
          </div>
        )}

        <p className="form-hint">
          이미지를 클릭하여 대표 이미지를 변경할 수 있습니다. 첫 번째 이미지가 기본
          대표 이미지입니다.
        </p>
      </div>

      {/* 태그 입력 */}
      <div className="form-field" style={{ marginTop: 'var(--space-6)' }}>
        <label className="form-label" htmlFor="tag-input">
          태그
        </label>
        <div
          className="tag-input-area"
          role="group"
          aria-label="태그 입력 영역"
          onClick={() => document.getElementById('tag-input')?.focus()}
        >
          {form.tags.map((tag) => (
            <span key={tag} className="tag tag--active tag--removable">
              {tag}
              <button
                type="button"
                className="tag__remove"
                aria-label={`${tag} 태그 제거`}
                onClick={(e) => {
                  e.stopPropagation()
                  removeTag(tag)
                }}
              >
                <svg
                  width="8"
                  height="8"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="3"
                  aria-hidden="true"
                >
                  <line x1="18" y1="6" x2="6" y2="18" />
                  <line x1="6" y1="6" x2="18" y2="18" />
                </svg>
              </button>
            </span>
          ))}
          <input
            type="text"
            id="tag-input"
            className="tag-input-area__input"
            placeholder={
              form.tags.length >= 10 ? '최대 10개까지 가능합니다' : '태그 입력 후 Enter'
            }
            value={tagInput}
            disabled={form.tags.length >= 10}
            onChange={(e) => setTagInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter') {
                e.preventDefault()
                addTag()
              }
            }}
            aria-label="새 태그 입력"
          />
        </div>
        <div className="form-counter">
          <span>{form.tags.length} / 10</span>
        </div>
        <p className="form-hint">
          태그를 입력하고 Enter를 누르면 추가됩니다. 최대 10개, 각 20자 이내
        </p>
      </div>
    </div>
  )
}

/* --------------------------------------------------------------------------
   Step 4: 공개 설정
   -------------------------------------------------------------------------- */
interface Step4Props {
  form: FormData
  onChange: (patch: Partial<FormData>) => void
}

function Step4Publish({ form, onChange }: Step4Props) {
  return (
    <div className="form-card__body">
      <fieldset style={{ border: 'none', padding: 0 }}>
        <legend
          className="form-label"
          style={{ marginBottom: 'var(--space-4)' }}
        >
          공개 여부
        </legend>
        <div className="publish-option-cards" role="radiogroup">
          {(
            [
              {
                value: 'DRAFT' as ItemStatus,
                icon: '📝',
                title: '임시 저장 (비공개)',
                desc: '상품을 저장하지만 아직 공개하지 않습니다. 언제든지 공개로 전환할 수 있습니다.',
              },
              {
                value: 'PUBLISHED' as ItemStatus,
                icon: '🚀',
                title: '즉시 공개',
                desc: '등록 즉시 상품 페이지가 공개되어 구매자가 바로 탐색하고 구매할 수 있습니다.',
              },
            ] as const
          ).map(({ value, icon, title, desc }) => {
            const selected = form.status === value
            const descId = `publish-desc-${value.toLowerCase()}`
            return (
              <label
                key={value}
                className={`publish-option-card ${selected ? 'publish-option-card--selected' : ''}`}
                aria-label={`${title}${selected ? ' (현재 선택됨)' : ''}`}
              >
                <input
                  type="radio"
                  name="status"
                  value={value}
                  checked={selected}
                  onChange={() => onChange({ status: value })}
                  aria-describedby={descId}
                />
                <span className="publish-option-card__check" aria-hidden="true" />
                <div className="publish-option-card__icon" aria-hidden="true">
                  {icon}
                </div>
                <div className="publish-option-card__title">{title}</div>
                <div className="publish-option-card__desc" id={descId}>
                  {desc}
                </div>
              </label>
            )
          })}
        </div>
      </fieldset>

      <div
        className="alert alert--info"
        style={{ marginTop: 'var(--space-6)' }}
        role="note"
      >
        <svg
          width="16"
          height="16"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          aria-hidden="true"
          style={{ flexShrink: 0, marginTop: 1 }}
        >
          <circle cx="12" cy="12" r="10" />
          <line x1="12" y1="8" x2="12" y2="12" />
          <line x1="12" y1="16" x2="12.01" y2="16" />
        </svg>
        <div>
          <strong>공개 전 확인사항:</strong> 등록 후 수익의 10%가 플랫폼 수수료로
          공제됩니다. 정산은 익월 15일에 진행됩니다.
        </div>
      </div>
    </div>
  )
}

/* --------------------------------------------------------------------------
   메인 페이지 컴포넌트
   -------------------------------------------------------------------------- */
export default function ItemNewPage() {
  const router = useRouter()
  const toast = useToast()
  const { requireAuth } = useAuth()
  const createItem = useCreateItem()

  const [currentStep, setCurrentStep] = useState(1)
  const [form, setFormRaw] = useState<FormData>(INITIAL_FORM)
  const [errors, setErrors] = useState<Record<string, string>>({})
  const [lastSaved, setLastSaved] = useState<Date | null>(null)

  // 인증 가드
  useEffect(() => {
    requireAuth('/items/new')
  }, [requireAuth])

  const onChange = useCallback(
    (patch: Partial<FormData> | ((prev: FormData) => Partial<FormData>)) => {
      setFormRaw((prev) => {
        const resolved = typeof patch === 'function' ? patch(prev) : patch
        return { ...prev, ...resolved }
      })
    },
    []
  )

  /* ------------ 유효성 검사 ------------ */
  const validateStep = (step: number): boolean => {
    const newErrors: Record<string, string> = {}

    if (step === 1) {
      if (!form.title.trim()) newErrors.title = '상품 제목을 입력해주세요.'
      if (!form.category) newErrors.category = '카테고리를 선택해주세요.'
      if (!form.description.trim())
        newErrors.description = '상품 설명을 입력해주세요.'
    }

    if (step === 2) {
      if (!form.saleType) newErrors.saleType = '판매 방식을 선택해주세요.'
      if (
        (form.saleType === 'PURCHASE' || form.saleType === 'BOTH') &&
        (form.price === '' || Number(form.price) < 100)
      ) {
        newErrors.price = '판매 가격은 100원 이상이어야 합니다.'
      }
      if (
        (form.saleType === 'SUBSCRIBE' || form.saleType === 'BOTH') &&
        form.plans.length === 0
      ) {
        newErrors.plans = '구독 플랜을 1개 이상 추가해주세요.'
      }
      if (form.plans.some((p) => !p.planName.trim())) {
        newErrors.plans = '모든 플랜의 이름을 입력해주세요.'
      }
      if (form.plans.some((p) => p.planPrice < 100)) {
        newErrors.plans = '모든 플랜의 가격은 100원 이상이어야 합니다.'
      }
    }

    if (step === 3) {
      if (form.images.length === 0)
        newErrors.images = '상품 이미지를 1장 이상 업로드해주세요.'
      if (form.images.some((img) => img.uploading))
        newErrors.images = '이미지 업로드가 완료될 때까지 기다려주세요.'
    }

    setErrors(newErrors)
    return Object.keys(newErrors).length === 0
  }

  /* ------------ 이전/다음 ------------ */
  const handlePrev = () => {
    setErrors({})
    setCurrentStep((s) => Math.max(1, s - 1))
  }

  const handleNext = () => {
    if (validateStep(currentStep)) {
      setCurrentStep((s) => Math.min(4, s + 1))
    }
  }

  /* ------------ 임시 저장 ------------ */
  const handleDraftSave = async () => {
    const payload = buildPayload('DRAFT')
    try {
      await createItem.mutateAsync(payload)
      setLastSaved(new Date())
      toast.success('임시 저장되었습니다.')
    } catch (e: any) {
      toast.error(e?.message ?? '임시 저장에 실패했습니다.')
    }
  }

  /* ------------ 최종 제출 ------------ */
  const handleSubmit = async () => {
    if (!validateStep(4)) return

    const payload = buildPayload(form.status)
    try {
      const result = await createItem.mutateAsync(payload)
      toast.success('상품이 등록되었습니다.')
      if (form.status === 'PUBLISHED') {
        router.push(`/items/${result.itemId}`)
      } else {
        router.push('/dashboard/shelf')
      }
    } catch (e: any) {
      toast.error(e?.message ?? '상품 등록에 실패했습니다.')
    }
  }

  const buildPayload = (status: ItemStatus) => {
    const uploadedIds = form.images
      .filter((img) => img.imageId)
      .map((img) => img.imageId as string)

    const subscriptionPlans: SubscriptionPlanRequest[] = form.plans.map((p) => ({
      planName: p.planName,
      period: p.period,
      planPrice: p.planPrice,
      description: p.description || undefined,
    }))

    return {
      title: form.title,
      description: form.description,
      category: form.category as ItemCategory,
      saleType: form.saleType as SaleType,
      price: Number(form.price) || 0,
      subscriptionPlans:
        form.saleType === 'SUBSCRIBE' || form.saleType === 'BOTH'
          ? subscriptionPlans
          : undefined,
      imageIds: uploadedIds,
      thumbnailIndex: form.thumbnailIndex,
      tags: form.tags.length > 0 ? form.tags : undefined,
      status,
    }
  }

  /* ------------ 완료된 스텝 헤더 렌더 ------------ */
  const renderCollapsedStep = (stepNum: number, title: string) => (
    <div
      className="form-card"
      style={{ marginBottom: 'var(--space-5)', opacity: 0.6 }}
      aria-label={`${stepNum}단계 완료`}
    >
      <div className="form-card__header">
        <span className="form-card__step-num" aria-hidden="true">
          <svg
            width="12"
            height="12"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="3"
            aria-hidden="true"
          >
            <polyline points="20 6 9 17 4 12" />
          </svg>
        </span>
        <span className="form-card__title">{title}</span>
        <button
          type="button"
          className="btn btn--ghost btn--sm"
          style={{ marginLeft: 'auto' }}
          aria-label={`${title} 수정`}
          onClick={() => {
            setErrors({})
            setCurrentStep(stepNum)
          }}
        >
          수정
        </button>
      </div>
    </div>
  )

  const renderLockedStep = (stepNum: number, title: string) => (
    <div
      className="form-card"
      style={{ marginTop: 'var(--space-5)', opacity: 0.4, pointerEvents: 'none' }}
      aria-label={`${stepNum}단계: ${title} (미완료)`}
    >
      <div className="form-card__header">
        <span
          className="form-card__step-num"
          style={{ backgroundColor: 'var(--color-border-strong)' }}
          aria-hidden="true"
        >
          {stepNum}
        </span>
        <span className="form-card__title">{title}</span>
      </div>
    </div>
  )

  return (
    <main className="page-body">
      <div className="register-layout">
        {/* 헤더 */}
        <div className="register-header">
          <a href="/dashboard/shelf" className="register-header__back">
            <svg
              width="16"
              height="16"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2.5"
              aria-hidden="true"
            >
              <path d="M19 12H5M12 5l-7 7 7 7" />
            </svg>
            내 선반으로
          </a>
          <h1 className="register-header__title">새 상품 등록</h1>
          <p className="register-header__desc">
            선반에 올릴 상품 정보를 입력해주세요. 언제든지 임시저장 후 나중에
            완성할 수 있습니다.
          </p>
        </div>

        {/* 자동저장 인디케이터 */}
        {lastSaved && (
          <div
            className="autosave-indicator"
            role="status"
            aria-live="polite"
            style={{ marginBottom: 'var(--space-4)' }}
          >
            <span className="autosave-indicator__dot" aria-hidden="true" />
            임시 저장됨 ({lastSaved.toLocaleTimeString('ko-KR')})
          </div>
        )}

        {/* 스텝 인디케이터 */}
        <StepIndicator currentStep={currentStep} />

        {/* Step 1 */}
        {currentStep > 1 && renderCollapsedStep(1, '기본 정보')}
        {currentStep === 1 && (
          <div className="form-card" aria-label="1단계: 기본 정보">
            <FormCardHeader
              stepNum={1}
              title="기본 정보"
              desc="상품의 기본 정보를 입력하세요"
            />
            <Step1BasicInfo form={form} onChange={onChange} errors={errors} />
            <div className="form-nav">
              <div className="form-nav__left" />
              <div className="form-nav__right">
                <Button variant="primary" onClick={handleNext}>
                  다음 단계
                  <svg
                    width="14"
                    height="14"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="2"
                    aria-hidden="true"
                  >
                    <path d="M5 12h14M12 5l7 7-7 7" />
                  </svg>
                </Button>
              </div>
            </div>
          </div>
        )}

        {/* Step 2 */}
        {currentStep > 2 && renderCollapsedStep(2, '판매 유형')}
        {currentStep < 2 && renderLockedStep(2, '판매 유형 및 가격 설정')}
        {currentStep === 2 && (
          <div className="form-card" id="step-2" aria-label="2단계: 판매 유형 선택">
            <FormCardHeader
              stepNum={2}
              title="판매 유형 및 가격 설정"
              desc="구매, 구독, 또는 둘 다 선택하세요"
            />
            <Step2SaleType form={form} onChange={onChange} errors={errors} />
            <div className="form-nav">
              <div className="form-nav__left">
                <Button variant="ghost" size="sm" onClick={handlePrev}>
                  <svg
                    width="14"
                    height="14"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="2"
                    aria-hidden="true"
                  >
                    <path d="M19 12H5M12 5l-7 7 7 7" />
                  </svg>
                  이전
                </Button>
              </div>
              <div className="form-nav__right">
                <Button variant="secondary" onClick={handleDraftSave} loading={createItem.isPending}>
                  임시 저장
                </Button>
                <Button variant="primary" onClick={handleNext}>
                  다음 단계
                  <svg
                    width="14"
                    height="14"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="2"
                    aria-hidden="true"
                  >
                    <path d="M5 12h14M12 5l7 7-7 7" />
                  </svg>
                </Button>
              </div>
            </div>
          </div>
        )}

        {/* Step 3 */}
        {currentStep > 3 && renderCollapsedStep(3, '이미지/태그')}
        {currentStep < 3 && renderLockedStep(3, '이미지 업로드 및 태그')}
        {currentStep === 3 && (
          <div
            className="form-card"
            id="step-3"
            aria-label="3단계: 이미지 업로드 및 태그"
          >
            <FormCardHeader
              stepNum={3}
              title="이미지 업로드 및 태그"
              desc="상품을 잘 표현하는 이미지를 추가하세요"
            />
            <Step3Images form={form} onChange={onChange} errors={errors} />
            <div className="form-nav">
              <div className="form-nav__left">
                <Button variant="ghost" size="sm" onClick={handlePrev}>
                  이전
                </Button>
              </div>
              <div className="form-nav__right">
                <Button variant="secondary" onClick={handleDraftSave} loading={createItem.isPending}>
                  임시 저장
                </Button>
                <Button variant="primary" onClick={handleNext}>
                  다음 단계
                </Button>
              </div>
            </div>
          </div>
        )}

        {/* Step 4 */}
        {currentStep < 4 && renderLockedStep(4, '공개 설정')}
        {currentStep === 4 && (
          <div className="form-card" id="step-4" aria-label="4단계: 공개 설정">
            <FormCardHeader
              stepNum={4}
              title="공개 설정"
              desc="상품을 지금 바로 공개하거나 나중에 공개할 수 있습니다"
            />
            <Step4Publish form={form} onChange={onChange} />
            <div className="form-nav">
              <div className="form-nav__left">
                <Button variant="ghost" size="sm" onClick={handlePrev}>
                  이전
                </Button>
              </div>
              <div className="form-nav__right">
                <Button
                  variant="secondary"
                  onClick={handleDraftSave}
                  loading={createItem.isPending}
                >
                  임시 저장
                </Button>
                <Button
                  variant="primary"
                  size="lg"
                  onClick={handleSubmit}
                  loading={createItem.isPending}
                >
                  <svg
                    width="16"
                    height="16"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="2.5"
                    aria-hidden="true"
                  >
                    <path d="M22 11.08V12a10 10 0 11-5.93-9.14" />
                    <polyline points="22 4 12 14.01 9 11.01" />
                  </svg>
                  상품 등록 완료
                </Button>
              </div>
            </div>
          </div>
        )}
      </div>
    </main>
  )
}
