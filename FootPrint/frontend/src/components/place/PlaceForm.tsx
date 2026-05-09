'use client';

import { useEffect, useState } from 'react';
import { useForm, Controller } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { useRouter } from 'next/navigation';
import type { PlaceDetail } from '@/types';
import { useCreatePlace, useUpdatePlace } from '@/lib/hooks/usePlaces';
import { useCategories } from '@/lib/hooks/useCategories';
import { useToast } from '@/components/common/useToast';
import Input from '@/components/common/Input';
import Rating from '@/components/common/Rating';
import Button from '@/components/common/Button';
import { cn } from '@/lib/utils';

const schema = z.object({
  name: z.string().min(1, '장소명을 입력하세요').max(100, '최대 100자'),
  address: z.string().optional(),
  latitude: z.coerce.number({ invalid_type_error: '위도를 입력하세요' }),
  longitude: z.coerce.number({ invalid_type_error: '경도를 입력하세요' }),
  visitedAt: z.string().min(1, '방문일을 선택하세요'),
  memo: z.string().max(2000, '최대 2,000자').optional(),
  rating: z.number().min(1).max(5).optional(),
  categoryIds: z.array(z.number()).min(1, '카테고리를 1개 이상 선택하세요'),
  tags: z.array(z.string()).optional(),
});

type FormValues = z.infer<typeof schema>;

interface PlaceFormProps {
  defaultValues?: PlaceDetail;
  mode: 'create' | 'edit';
}

export default function PlaceForm({ defaultValues, mode }: PlaceFormProps) {
  const router = useRouter();
  const toast = useToast();
  const { data: categories = [] } = useCategories();

  const [tagInput, setTagInput] = useState('');
  const [tags, setTags] = useState<string[]>(defaultValues?.tags ?? []);

  const createPlace = useCreatePlace();
  const updatePlace = useUpdatePlace(defaultValues?.id ?? 0);

  const {
    register,
    handleSubmit,
    control,
    setValue,
    watch,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: {
      name: defaultValues?.name ?? '',
      address: defaultValues?.address ?? '',
      latitude: defaultValues?.latitude ?? ('' as unknown as number),
      longitude: defaultValues?.longitude ?? ('' as unknown as number),
      visitedAt: defaultValues?.visitedAt?.slice(0, 10) ?? '',
      memo: defaultValues?.memo ?? '',
      rating: defaultValues?.rating,
      categoryIds: defaultValues?.categories.map((c) => c.id) ?? [],
      tags: defaultValues?.tags ?? [],
    },
  });

  const selectedCategoryIds = watch('categoryIds') ?? [];

  const toggleCategory = (id: number) => {
    const current = selectedCategoryIds;
    if (current.includes(id)) {
      setValue('categoryIds', current.filter((c) => c !== id), { shouldValidate: true });
    } else {
      setValue('categoryIds', [...current, id], { shouldValidate: true });
    }
  };

  const addTag = () => {
    const t = tagInput.trim();
    if (t && !tags.includes(t)) {
      const next = [...tags, t];
      setTags(next);
      setValue('tags', next);
    }
    setTagInput('');
  };

  const removeTag = (t: string) => {
    const next = tags.filter((tag) => tag !== t);
    setTags(next);
    setValue('tags', next);
  };

  const onSubmit = async (values: FormValues) => {
    try {
      const payload = { ...values, tags };
      if (mode === 'create') {
        await createPlace.mutateAsync(payload);
        toast.success('장소가 등록되었습니다.');
        router.push('/places');
      } else {
        await updatePlace.mutateAsync(payload);
        toast.success('장소가 수정되었습니다.');
        router.push(`/places/${defaultValues?.id}`);
      }
    } catch {
      toast.error('저장에 실패했습니다. 다시 시도해주세요.');
    }
  };

  return (
    <form onSubmit={handleSubmit(onSubmit)} noValidate>
      <div className="max-w-[680px] mx-auto px-6 py-8 pb-24">

        {/* 위치 정보 섹션 */}
        <div className="bg-white border border-[#E7E5E4] rounded-[16px] p-6 mb-4">
          <h2 className="text-[15px] font-bold text-[#1C1917] mb-4 flex items-center gap-2">
            <span>📍</span> 위치 정보
          </h2>
          <Input
            label="주소"
            placeholder="주소를 입력하세요"
            register={register('address')}
            error={errors.address?.message}
            className="mb-4"
          />
          <div className="grid grid-cols-2 gap-3">
            <Input
              label="위도"
              required
              type="number"
              step="any"
              placeholder="37.5795"
              register={register('latitude')}
              error={errors.latitude?.message}
            />
            <Input
              label="경도"
              required
              type="number"
              step="any"
              placeholder="126.9770"
              register={register('longitude')}
              error={errors.longitude?.message}
            />
          </div>
        </div>

        {/* 기본 정보 섹션 */}
        <div className="bg-white border border-[#E7E5E4] rounded-[16px] p-6 mb-4">
          <h2 className="text-[15px] font-bold text-[#1C1917] mb-4 flex items-center gap-2">
            <span>📝</span> 기본 정보
          </h2>
          <div className="flex flex-col gap-4">
            <Input
              label="장소명"
              required
              placeholder="장소명을 입력하세요 (최대 100자)"
              register={register('name')}
              error={errors.name?.message}
            />
            <Input
              label="방문일"
              required
              type="date"
              register={register('visitedAt')}
              error={errors.visitedAt?.message}
            />

            {/* 평점 */}
            <div className="flex flex-col gap-1.5">
              <label className="text-[13px] font-bold text-[#44403C]">평점</label>
              <Controller
                name="rating"
                control={control}
                render={({ field }) => (
                  <Rating value={field.value} onChange={field.onChange} size="lg" />
                )}
              />
            </div>

            {/* 메모 */}
            <div className="flex flex-col gap-1.5">
              <label className="text-[13px] font-bold text-[#44403C]">메모</label>
              <textarea
                {...register('memo')}
                placeholder="이 장소에 대한 기억을 남겨보세요... (최대 2,000자)"
                className="w-full border-[1.5px] border-[#E7E5E4] rounded-[10px] px-3.5 py-2.5 text-[14px] text-[#1C1917] bg-white resize-y min-h-[100px] outline-none focus:border-[#F97316] placeholder:text-[#A8A29E] transition-colors"
              />
              {errors.memo && (
                <p className="text-[12px] text-[#DC2626]">{errors.memo.message}</p>
              )}
            </div>
          </div>
        </div>

        {/* 카테고리 섹션 */}
        <div className="bg-white border border-[#E7E5E4] rounded-[16px] p-6 mb-4">
          <h2 className="text-[15px] font-bold text-[#1C1917] mb-4 flex items-center gap-2">
            <span>🏷️</span> 카테고리
            <span className="text-[#F97316]">*</span>
          </h2>
          <div className="flex gap-2 flex-wrap">
            {categories.map((cat) => (
              <button
                key={cat.id}
                type="button"
                onClick={() => toggleCategory(cat.id)}
                className={cn(
                  'px-3.5 py-1.5 rounded-full text-[13px] font-semibold border-[1.5px] transition-colors cursor-pointer',
                  selectedCategoryIds.includes(cat.id)
                    ? 'border-[#F97316] bg-[#FFF8F0] text-[#F97316]'
                    : 'border-[#E7E5E4] bg-white text-[#78716C]'
                )}
              >
                {cat.name}
              </button>
            ))}
          </div>
          {errors.categoryIds && (
            <p className="text-[12px] text-[#DC2626] mt-2">{errors.categoryIds.message}</p>
          )}
        </div>

        {/* 태그 섹션 */}
        <div className="bg-white border border-[#E7E5E4] rounded-[16px] p-6 mb-4">
          <h2 className="text-[15px] font-bold text-[#1C1917] mb-4 flex items-center gap-2">
            <span>🔖</span> 태그
          </h2>
          <div className="flex gap-2 mb-3">
            <input
              type="text"
              value={tagInput}
              onChange={(e) => setTagInput(e.target.value)}
              onKeyDown={(e) => { if (e.key === 'Enter') { e.preventDefault(); addTag(); } }}
              placeholder="태그 입력 후 Enter"
              className="flex-1 border-[1.5px] border-[#E7E5E4] rounded-[10px] px-3.5 py-2 text-[14px] outline-none focus:border-[#F97316] placeholder:text-[#A8A29E]"
            />
            <Button type="button" variant="secondary" size="sm" onClick={addTag}>추가</Button>
          </div>
          {tags.length > 0 && (
            <div className="flex gap-2 flex-wrap">
              {tags.map((t) => (
                <span
                  key={t}
                  className="flex items-center gap-1 px-3 py-1 bg-[#F5F5F0] text-[#78716C] text-[13px] rounded-full"
                >
                  #{t}
                  <button
                    type="button"
                    onClick={() => removeTag(t)}
                    className="text-[#A8A29E] hover:text-[#DC2626] transition-colors cursor-pointer ml-0.5"
                  >
                    ×
                  </button>
                </span>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* 하단 고정 버튼 */}
      <div className="fixed bottom-0 left-0 right-0 bg-white border-t border-[#E7E5E4] px-6 py-4 flex gap-3 z-50">
        <Button
          type="button"
          variant="secondary"
          size="lg"
          className="flex-1"
          onClick={() => router.back()}
        >
          취소
        </Button>
        <Button
          type="submit"
          variant="primary"
          size="lg"
          loading={isSubmitting}
          className="flex-[2]"
        >
          {mode === 'create' ? '등록하기' : '수정하기'}
        </Button>
      </div>
    </form>
  );
}
