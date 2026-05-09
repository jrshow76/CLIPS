'use client'

/**
 * SCR-023 상품 수정 페이지
 * 등록 폼과 동일한 4단계 구조, 기존 데이터 프리필
 */

import { useState, useCallback, useRef, useEffect } from 'react'
import { useRouter, useParams } from 'next/navigation'
import { Button } from '@/components/common/Button'
import { useToast } from '@/components/common/Toast'
import { useItem, useUpdateItem } from '@/hooks/useItems'
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
   타입 정의 (등록 폼과 동일)
   -------------------------------------------------------------------------- */
interface PlanDraft {
  id: string
  planId?: number
  planName: string
  period: SubscriptionPeriod
  planPrice: number
  description: string
}

interface ImagePreview {
  file?: File
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

function makePlanId() {
  return `plan-${Date.now()}-${Math.random().toString(36).slice(2)}`
}

/* --------------------------------------------------------------------------
   Step Indicator
   -------------------------------------------------------------------------- */
const STEP_LABELS = ['기본 정보', '판매 유형', '이미지/태그', '공개 설정']

function StepIndicator({ currentStep }: { currentStep: number }) {
  return (
    <div className="step-indicator" role="list" aria-label="수정 단계">
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
              <div className="step__circle">
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
function Step1BasicInfo({
  form,
  onChange,
  errors,
}: {
  form: FormData
  onChange: (p: Partial<FormData>) => void
  errors: Record<string, string>
}) {
  return (
    <div className="form-card__body">
      <div className="form-field">
        <label className="form-label form-label--required" htmlFor="edit-title">
          상품 제목
        </label>
        <input
          type="text"
          id="edit-title"
          className={`form-input ${errors.title ? 'form-input--error' : ''}`}
          placeholder="상품 제목을 입력하세요 (최대 100자)"
          value={form.title}
          maxLength={100}
          onChange={(e) => onChange({ title: e.target.value })}
          aria-invalid={!!errors.title}
        />
        {errors.title && (
          <p className="form-error" role="alert">
            {errors.title}
          </p>
        )}
      </div>

      <div
        className="form-row form-row--2col"
        style={{ marginTop: 'var(--space-5)' }}
      >
        <div className="form-field">
          <label
            className="form-label form-label--required"
            htmlFor="edit-category"
          >
            카테고리
          </label>
          <select
            id="edit-category"
            className="form-select"
            value={form.category}
            onChange={(e) =>
              onChange({ category: e.target.value as ItemCategory })
            }
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
            <p className="form-error" role="alert">
              {errors.category}
            </p>
          )}
        </div>
      </div>

      <div className="form-field" style={{ marginTop: 'var(--space-5)' }}>
        <label
          className="form-label form-label--required"
          htmlFor="edit-description"
        >
          상품 설명
        </label>
        <textarea
          id="edit-description"
          className="form-textarea form-textarea--grow"
          placeholder="상품에 대한 상세 설명을 입력하세요"
          value={form.description}
          maxLength={5000}
          onChange={(e) => onChange({ description: e.target.value })}
          aria-invalid={!!errors.description}
        />
        {errors.description && (
          <p className="form-error" role="alert">
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
function Step2SaleType({
  form,
  onChange,
  errors,
}: {
  form: FormData
  onChange: (p: Partial<FormData>) => void
  errors: Record<string, string>
}) {
  const addPlan = () => {
    onChange({
      plans: [
        ...form.plans,
        {
          id: makePlanId(),
          planName: '',
          period: 'MONTHLY',
          planPrice: 0,
          description: '',
        },
      ],
    })
  }

  const removePlan = (id: string) => {
    onChange({ plans: form.plans.filter((p) => p.id !== id) })
  }

  const updatePlan = (id: string, patch: Partial<PlanDraft>) => {
    onChange({
      plans: form.plans.map((p) => (p.id === id ? { ...p, ...patch } : p)),
    })
  }

  const showPurchasePrice =
    form.saleType === 'PURCHASE' || form.saleType === 'BOTH'
  const showPlans = form.saleType === 'SUBSCRIBE' || form.saleType === 'BOTH'

  return (
    <div className="form-card__body">
      <fieldset
        style={{ border: 'none', padding: 0, marginBottom: 'var(--space-8)' }}
      >
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
        </legend>
        {errors.saleType && (
          <p
            className="form-error"
            role="alert"
            style={{ marginBottom: 'var(--space-3)' }}
          >
            {errors.saleType}
          </p>
        )}
        <div className="sale-type-cards" role="radiogroup">
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
            return (
              <label
                key={value}
                className={`sale-type-card ${selected ? 'sale-type-card--selected' : ''}`}
              >
                <input
                  type="radio"
                  name="edit-saleType"
                  value={value}
                  checked={selected}
                  onChange={() => onChange({ saleType: value })}
                />
                <div
                  className="sale-type-card__selected-mark"
                  aria-hidden="true"
                />
                <div className="sale-type-card__icon" aria-hidden="true">
                  {icon}
                </div>
                <div className="sale-type-card__title">{title}</div>
                <div className="sale-type-card__desc">{desc}</div>
              </label>
            )
          })}
        </div>
      </fieldset>

      {showPurchasePrice && (
        <div
          className="pricing-section"
          style={{ marginBottom: 'var(--space-5)' }}
        >
          <div className="pricing-section__header">단일 구매 가격</div>
          <div className="pricing-section__body">
            <div className="form-field">
              <label
                className="form-label form-label--required"
                htmlFor="edit-price"
              >
                판매 가격
              </label>
              <div className="price-input-wrap">
                <span
                  className="price-input-wrap__symbol"
                  aria-hidden="true"
                >
                  ₩
                </span>
                <input
                  type="number"
                  id="edit-price"
                  className="form-input"
                  placeholder="0"
                  min={100}
                  value={form.price}
                  onChange={(e) =>
                    onChange({
                      price: e.target.value === '' ? '' : Number(e.target.value),
                    })
                  }
                  aria-label="판매 가격 (원)"
                />
              </div>
              {errors.price && (
                <p className="form-error" role="alert">
                  {errors.price}
                </p>
              )}
            </div>
          </div>
        </div>
      )}

      {showPlans && (
        <div className="pricing-section">
          <div className="pricing-section__header">구독 플랜 설정</div>
          <div className="pricing-section__body">
            {errors.plans && (
              <p
                className="form-error"
                role="alert"
                style={{ marginBottom: 'var(--space-3)' }}
              >
                {errors.plans}
              </p>
            )}
            <div className="plan-list" role="list">
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
                        <span
                          className="price-input-wrap__symbol"
                          aria-hidden="true"
                        >
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
                        />
                      </div>
                    </div>
                  </div>
                  <div
                    className="form-field"
                    style={{ marginTop: 'var(--space-3)' }}
                  >
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
   Step 3: 이미지/태그
   -------------------------------------------------------------------------- */
function Step3Images({
  form,
  onChange,
  errors,
}: {
  form: FormData
  onChange: (p: Partial<FormData>) => void
  errors: Record<string, string>
}) {
  const [isDragOver, setIsDragOver] = useState(false)
  const [tagInput, setTagInput] = useState('')
  const fileInputRef = useRef<HTMLInputElement>(null)
  const currentImagesRef = useRef<ImagePreview[]>(form.images)
  currentImagesRef.current = form.images

  const handleFiles = async (files: FileList) => {
    const remaining = 10 - currentImagesRef.current.length
    if (remaining <= 0) return

    const newFiles = Array.from(files)
      .slice(0, remaining)
      .filter(
        (f) =>
          ['image/jpeg', 'image/png', 'image/webp'].includes(f.type) &&
          f.size <= 10 * 1024 * 1024
      )

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
        const uploaded = await uploadFile(preview.file!, 'ITEM_IMAGE')
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

  const addTag = () => {
    const trimmed = tagInput.trim()
    if (!trimmed || form.tags.includes(trimmed) || form.tags.length >= 10)
      return
    onChange({ tags: [...form.tags, trimmed] })
    setTagInput('')
  }

  const removeTag = (tag: string) => {
    onChange({ tags: form.tags.filter((t) => t !== tag) })
  }

  return (
    <div className="form-card__body">
      <div className="form-field">
        <span className="form-label form-label--required" id="edit-image-label">
          상품 이미지
        </span>
        {errors.images && (
          <p
            className="form-error"
            role="alert"
            style={{ marginBottom: 'var(--space-2)' }}
          >
            {errors.images}
          </p>
        )}
        <div
          className={`image-upload-zone ${isDragOver ? 'image-upload-zone--dragover' : ''}`}
          role="button"
          tabIndex={0}
          aria-labelledby="edit-image-label"
          onClick={() => fileInputRef.current?.click()}
          onKeyDown={(e) => {
            if (e.key === 'Enter' || e.key === ' ')
              fileInputRef.current?.click()
          }}
          onDragOver={(e) => {
            e.preventDefault()
            setIsDragOver(true)
          }}
          onDragLeave={() => setIsDragOver(false)}
          onDrop={(e) => {
            e.preventDefault()
            setIsDragOver(false)
            if (e.dataTransfer.files.length > 0)
              handleFiles(e.dataTransfer.files)
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
          <div className="image-upload-zone__desc">
            <strong>JPG, PNG, WEBP</strong> 지원 · 최대 10장
          </div>
        </div>

        {form.images.length > 0 && (
          <div className="image-preview-grid" role="list">
            {form.images.map((img, idx) => {
              const isThumbnail = idx === form.thumbnailIndex
              return (
                <div
                  key={img.previewUrl}
                  className={`image-preview-item ${isThumbnail ? 'image-preview-item--thumbnail' : ''}`}
                  role="listitem"
                >
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img
                    src={img.previewUrl}
                    alt={`이미지 ${idx + 1}`}
                    className="image-preview-item__img"
                    style={{ opacity: img.uploading ? 0.5 : 1 }}
                  />
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
                  </div>
                  {isThumbnail && (
                    <span className="image-preview-item__thumb-badge">대표</span>
                  )}
                </div>
              )
            })}
          </div>
        )}
      </div>

      <div className="form-field" style={{ marginTop: 'var(--space-6)' }}>
        <label className="form-label" htmlFor="edit-tag-input">
          태그
        </label>
        <div
          className="tag-input-area"
          role="group"
          aria-label="태그 입력 영역"
          onClick={() => document.getElementById('edit-tag-input')?.focus()}
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
            id="edit-tag-input"
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
          />
        </div>
        <div className="form-counter">
          <span>{form.tags.length} / 10</span>
        </div>
      </div>
    </div>
  )
}

/* --------------------------------------------------------------------------
   Step 4: 공개 설정
   -------------------------------------------------------------------------- */
function Step4Publish({
  form,
  onChange,
}: {
  form: FormData
  onChange: (p: Partial<FormData>) => void
}) {
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
                desc: '상품을 저장하지만 아직 공개하지 않습니다.',
              },
              {
                value: 'PUBLISHED' as ItemStatus,
                icon: '🚀',
                title: '즉시 공개',
                desc: '등록 즉시 상품 페이지가 공개됩니다.',
              },
            ] as const
          ).map(({ value, icon, title, desc }) => {
            const selected = form.status === value
            return (
              <label
                key={value}
                className={`publish-option-card ${selected ? 'publish-option-card--selected' : ''}`}
              >
                <input
                  type="radio"
                  name="edit-status"
                  value={value}
                  checked={selected}
                  onChange={() => onChange({ status: value })}
                />
                <span className="publish-option-card__check" aria-hidden="true" />
                <div className="publish-option-card__icon" aria-hidden="true">
                  {icon}
                </div>
                <div className="publish-option-card__title">{title}</div>
                <div className="publish-option-card__desc">{desc}</div>
              </label>
            )
          })}
        </div>
      </fieldset>
    </div>
  )
}

/* --------------------------------------------------------------------------
   메인 페이지 컴포넌트
   -------------------------------------------------------------------------- */
export default function ItemEditPage() {
  const router = useRouter()
  const params = useParams()
  const itemId = Number(params.id)

  const toast = useToast()
  const { requireAuth, user } = useAuth()
  const { data: item, isLoading, isError } = useItem(itemId)
  const updateItem = useUpdateItem(itemId)

  const [currentStep, setCurrentStep] = useState(1)
  const [form, setFormRaw] = useState<FormData | null>(null)
  const [errors, setErrors] = useState<Record<string, string>>({})
  const [initialized, setInitialized] = useState(false)

  // 인증 가드
  useEffect(() => {
    requireAuth(`/items/${itemId}/edit`)
  }, [requireAuth, itemId])

  // 기존 데이터 프리필
  useEffect(() => {
    if (item && !initialized) {
      const prefilled: FormData = {
        title: item.title,
        category: item.category,
        description: item.description,
        saleType: item.saleType,
        price: item.price,
        plans: item.subscriptionPlans.map((p) => ({
          id: makePlanId(),
          planId: p.planId,
          planName: p.planName,
          period: p.period,
          planPrice: p.planPrice,
          description: p.description ?? '',
        })),
        images: item.images.map((img) => ({
          previewUrl: img.url,
          imageId: img.imageId,
          uploading: false,
        })),
        thumbnailIndex: Math.max(
          0,
          item.images.findIndex((img) => img.isThumbnail)
        ),
        tags: item.tags ?? [],
        status: item.status === 'DELETED' ? 'DRAFT' : item.status,
      }
      setFormRaw(prefilled)
      setInitialized(true)
    }
  }, [item, initialized])

  // 본인 상품 여부 확인
  useEffect(() => {
    if (item && user && item.seller.userId !== user.userId) {
      toast.error('수정 권한이 없습니다.')
      router.replace('/dashboard/shelf')
    }
  }, [item, user, router, toast])

  const onChange = useCallback(
    (patch: Partial<FormData> | ((prev: FormData) => Partial<FormData>)) => {
      setFormRaw((prev) => {
        if (!prev) return prev
        const resolved = typeof patch === 'function' ? patch(prev) : patch
        return { ...prev, ...resolved }
      })
    },
    []
  )

  const validateStep = (step: number): boolean => {
    if (!form) return false
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

  const handlePrev = () => {
    setErrors({})
    setCurrentStep((s) => Math.max(1, s - 1))
  }

  const handleNext = () => {
    if (validateStep(currentStep)) setCurrentStep((s) => Math.min(4, s + 1))
  }

  const handleSubmit = async () => {
    if (!form || !validateStep(4)) return

    const uploadedIds = form.images
      .filter((img) => img.imageId)
      .map((img) => img.imageId as string)

    const subscriptionPlans: SubscriptionPlanRequest[] = form.plans.map(
      (p) => ({
        planName: p.planName,
        period: p.period,
        planPrice: p.planPrice,
        description: p.description || undefined,
      })
    )

    const payload = {
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
      status: form.status,
    }

    try {
      await updateItem.mutateAsync(payload)
      toast.success('상품이 수정되었습니다.')
      if (form.status === 'PUBLISHED') {
        router.push(`/items/${itemId}`)
      } else {
        router.push('/dashboard/shelf')
      }
    } catch (e: any) {
      toast.error(e?.message ?? '상품 수정에 실패했습니다.')
    }
  }

  const renderCollapsedStep = (stepNum: number, title: string) => (
    <div
      className="form-card"
      style={{ marginBottom: 'var(--space-5)', opacity: 0.6 }}
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
          >
            <polyline points="20 6 9 17 4 12" />
          </svg>
        </span>
        <span className="form-card__title">{title}</span>
        <button
          type="button"
          className="btn btn--ghost btn--sm"
          style={{ marginLeft: 'auto' }}
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
    >
      <div className="form-card__header">
        <span
          className="form-card__step-num"
          style={{ backgroundColor: 'var(--color-border-strong)' }}
        >
          {stepNum}
        </span>
        <span className="form-card__title">{title}</span>
      </div>
    </div>
  )

  /* 로딩/에러 상태 */
  if (isLoading) {
    return (
      <main className="page-body">
        <div className="register-layout">
          <div
            style={{
              textAlign: 'center',
              padding: 'var(--space-20)',
              color: 'var(--color-text-tertiary)',
            }}
          >
            상품 정보를 불러오는 중...
          </div>
        </div>
      </main>
    )
  }

  if (isError || !item) {
    return (
      <main className="page-body">
        <div className="register-layout">
          <div
            style={{
              textAlign: 'center',
              padding: 'var(--space-20)',
              color: 'var(--color-error)',
            }}
          >
            상품 정보를 불러올 수 없습니다.
          </div>
        </div>
      </main>
    )
  }

  if (!form) return null

  return (
    <main className="page-body">
      <div className="register-layout">
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
          <h1 className="register-header__title">상품 수정</h1>
          <p className="register-header__desc">
            상품 정보를 수정합니다. 수정 사항은 저장 후 반영됩니다.
          </p>
        </div>

        <StepIndicator currentStep={currentStep} />

        {/* Step 1 */}
        {currentStep > 1 && renderCollapsedStep(1, '기본 정보')}
        {currentStep === 1 && (
          <div className="form-card">
            <FormCardHeader stepNum={1} title="기본 정보" />
            <Step1BasicInfo form={form} onChange={onChange} errors={errors} />
            <div className="form-nav">
              <div className="form-nav__left" />
              <div className="form-nav__right">
                <Button variant="primary" onClick={handleNext}>
                  다음 단계
                </Button>
              </div>
            </div>
          </div>
        )}

        {/* Step 2 */}
        {currentStep > 2 && renderCollapsedStep(2, '판매 유형')}
        {currentStep < 2 && renderLockedStep(2, '판매 유형 및 가격 설정')}
        {currentStep === 2 && (
          <div className="form-card">
            <FormCardHeader
              stepNum={2}
              title="판매 유형 및 가격 설정"
              desc="구매, 구독, 또는 둘 다 선택하세요"
            />
            <Step2SaleType form={form} onChange={onChange} errors={errors} />
            <div className="form-nav">
              <div className="form-nav__left">
                <Button variant="ghost" size="sm" onClick={handlePrev}>
                  이전
                </Button>
              </div>
              <div className="form-nav__right">
                <Button variant="primary" onClick={handleNext}>
                  다음 단계
                </Button>
              </div>
            </div>
          </div>
        )}

        {/* Step 3 */}
        {currentStep > 3 && renderCollapsedStep(3, '이미지/태그')}
        {currentStep < 3 && renderLockedStep(3, '이미지 업로드 및 태그')}
        {currentStep === 3 && (
          <div className="form-card">
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
          <div className="form-card">
            <FormCardHeader
              stepNum={4}
              title="공개 설정"
              desc="상품을 지금 바로 공개하거나 비공개로 유지할 수 있습니다"
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
                  variant="primary"
                  size="lg"
                  onClick={handleSubmit}
                  loading={updateItem.isPending}
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
                  수정 완료
                </Button>
              </div>
            </div>
          </div>
        )}
      </div>
    </main>
  )
}
