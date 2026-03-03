interface SkeletonProps {
  className?: string;
}

export function Skeleton({ className = '' }: SkeletonProps) {
  return (
    <div className={`animate-pulse rounded bg-slate-200 ${className}`} />
  );
}

export function CardSkeleton() {
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-6">
      <div className="flex items-start justify-between mb-4">
        <Skeleton className="w-10 h-10 rounded-lg" />
        <Skeleton className="w-16 h-5 rounded-full" />
      </div>
      <Skeleton className="h-5 w-2/3 mb-2" />
      <Skeleton className="h-4 w-full mb-1" />
      <Skeleton className="h-4 w-4/5" />
    </div>
  );
}

export function SectionSkeleton() {
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-5">
      <div className="flex items-center gap-3 mb-3">
        <Skeleton className="w-7 h-7 rounded-lg" />
        <Skeleton className="h-4 w-48" />
      </div>
      <div className="ml-10 space-y-2">
        <Skeleton className="h-3 w-full" />
        <Skeleton className="h-3 w-3/4" />
      </div>
    </div>
  );
}

export function RadarChartSkeleton() {
  return (
    <div className="bg-slate-50 rounded-xl p-2 flex items-center justify-center h-[280px]">
      <div className="text-center">
        <Skeleton className="w-20 h-20 rounded-full mx-auto mb-2" />
        <Skeleton className="h-3 w-12 mx-auto" />
      </div>
    </div>
  );
}

export function LoadingSpinner() {
  return (
    <div className="flex items-center justify-center py-16">
      <div className="w-8 h-8 border-2 border-slate-200 border-t-blue-600 rounded-full animate-spin" />
    </div>
  );
}
