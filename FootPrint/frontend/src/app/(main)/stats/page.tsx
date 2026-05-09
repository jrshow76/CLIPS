'use client';

import { useStatsSummary, useMonthlyStats, useCategoryStats } from '@/lib/hooks/useStats';
import Loading from '@/components/common/Loading';

const MONTH_LABELS = ['1월', '2월', '3월', '4월', '5월', '6월', '7월', '8월', '9월', '10월', '11월', '12월'];

const CATEGORY_COLORS = [
  '#F97316', '#0EA5E9', '#16A34A', '#7C3AED', '#D97706', '#DC2626', '#0891B2', '#15803D',
];

export default function StatsPage() {
  const { data: summary, isLoading: summaryLoading } = useStatsSummary();
  const { data: monthly = [], isLoading: monthlyLoading } = useMonthlyStats();
  const { data: categoryStats = [], isLoading: categoryLoading } = useCategoryStats();

  const isLoading = summaryLoading || monthlyLoading || categoryLoading;

  if (isLoading) {
    return (
      <div className="flex justify-center items-center py-20">
        <Loading size="lg" />
      </div>
    );
  }

  // 월별 차트 최대값 계산
  const maxMonthlyCount = Math.max(...monthly.map((m) => m.count), 1);

  // 카테고리 통계 전체 합
  const totalCategoryCount = categoryStats.reduce((sum, c) => sum + c.count, 0);

  return (
    <div className="max-w-[900px] mx-auto px-6 py-8">
      <h1 className="text-[24px] font-extrabold text-[#1C1917] mb-8">나의 통계</h1>

      {/* 요약 카드 */}
      <div className="grid grid-cols-3 gap-4 mb-8 max-sm:grid-cols-1">
        <div className="bg-white border border-[#E7E5E4] rounded-[16px] p-6">
          <p className="text-[13px] text-[#A8A29E] font-semibold mb-2">총 방문 장소</p>
          <p className="text-[36px] font-extrabold text-[#F97316]">
            {summary?.totalPlaces ?? 0}
            <span className="text-[16px] font-semibold text-[#78716C] ml-1">곳</span>
          </p>
        </div>
        <div className="bg-white border border-[#E7E5E4] rounded-[16px] p-6">
          <p className="text-[13px] text-[#A8A29E] font-semibold mb-2">이번 달 방문</p>
          <p className="text-[36px] font-extrabold text-[#0EA5E9]">
            {summary?.thisMonthPlaces ?? 0}
            <span className="text-[16px] font-semibold text-[#78716C] ml-1">곳</span>
          </p>
        </div>
        <div className="bg-white border border-[#E7E5E4] rounded-[16px] p-6">
          <p className="text-[13px] text-[#A8A29E] font-semibold mb-2">평균 평점</p>
          <p className="text-[36px] font-extrabold text-[#F59E0B]">
            {summary?.avgRating?.toFixed(1) ?? '-'}
            <span className="text-[16px] font-semibold text-[#78716C] ml-1">점</span>
          </p>
          {summary?.topCategory && (
            <p className="text-[12px] text-[#A8A29E] mt-1">
              최다 방문: {summary.topCategory.name}
            </p>
          )}
        </div>
      </div>

      {/* 월별 방문 차트 */}
      <div className="bg-white border border-[#E7E5E4] rounded-[16px] p-6 mb-8">
        <h2 className="text-[17px] font-bold text-[#1C1917] mb-6">월별 방문 현황</h2>
        {monthly.length === 0 ? (
          <div className="text-center py-8 text-[#A8A29E]">데이터가 없습니다</div>
        ) : (
          <div className="flex items-end gap-2 h-[180px]">
            {MONTH_LABELS.map((label, idx) => {
              const month = idx + 1;
              const stat = monthly.find((m) => m.month === month);
              const count = stat?.count ?? 0;
              const heightPct = (count / maxMonthlyCount) * 100;

              return (
                <div key={label} className="flex-1 flex flex-col items-center gap-1">
                  {count > 0 && (
                    <span className="text-[11px] text-[#78716C] font-semibold">{count}</span>
                  )}
                  <div
                    className="w-full rounded-t-lg transition-all duration-500"
                    style={{
                      height: `${Math.max(heightPct, count > 0 ? 8 : 0)}%`,
                      backgroundColor: count > 0 ? '#F97316' : '#F5F5F0',
                      minHeight: '4px',
                    }}
                  />
                  <span className="text-[10px] text-[#A8A29E] whitespace-nowrap">{label}</span>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* 카테고리별 분포 */}
      <div className="bg-white border border-[#E7E5E4] rounded-[16px] p-6">
        <h2 className="text-[17px] font-bold text-[#1C1917] mb-6">카테고리별 분포</h2>
        {categoryStats.length === 0 ? (
          <div className="text-center py-8 text-[#A8A29E]">데이터가 없습니다</div>
        ) : (
          <div className="flex flex-col gap-4">
            {categoryStats.map((cs, idx) => {
              const pct = totalCategoryCount > 0
                ? Math.round((cs.count / totalCategoryCount) * 100)
                : 0;
              const color = CATEGORY_COLORS[idx % CATEGORY_COLORS.length];

              return (
                <div key={cs.category.id}>
                  <div className="flex items-center justify-between mb-1.5">
                    <span className="text-[14px] font-semibold text-[#1C1917]">
                      {cs.category.name}
                    </span>
                    <span className="text-[13px] text-[#78716C]">
                      {cs.count}곳 ({pct}%)
                    </span>
                  </div>
                  {/* 원형 퍼센트 바 (선형 프로그레스 바) */}
                  <div className="h-2.5 bg-[#F5F5F0] rounded-full overflow-hidden">
                    <div
                      className="h-full rounded-full transition-all duration-700"
                      style={{ width: `${pct}%`, backgroundColor: color }}
                    />
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
