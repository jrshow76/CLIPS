export default function GlobalLoading() {
  return (
    <div className="center" style={{ minHeight: '100vh' }}>
      <div className="stack items-center gap-3">
        <div className="border-brand-500 h-8 w-8 animate-spin rounded-full border-2 border-r-transparent" />
        <p className="text-muted text-sm">불러오는 중...</p>
      </div>
    </div>
  );
}
