import dynamic from 'next/dynamic';

// 디자이너는 client-only (SSR 제외)
const ReportDesigner = dynamic(
  () => import('@/components/designer/ReportDesigner'),
  { ssr: false, loading: () => (
    <div className="flex items-center justify-center h-screen bg-designer-bg text-gray-400">
      로딩 중...
    </div>
  )},
);

export default function DesignerPage() {
  return <ReportDesigner />;
}
