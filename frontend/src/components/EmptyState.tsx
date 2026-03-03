import { BookOpen, WifiOff, Database } from 'lucide-react';

interface EmptyStateProps {
  variant: 'no-guides' | 'no-docs' | 'connection-lost';
  onAction?: () => void;
}

const variants = {
  'no-guides': {
    Icon: BookOpen,
    title: 'No guides yet',
    description: 'Generate your first onboarding guide to see it here.',
    actionLabel: 'Create Guide',
  },
  'no-docs': {
    Icon: Database,
    title: 'Documentation not yet ingested',
    description: 'Run `make ingest` to load documents before generating guides.',
    actionLabel: undefined,
  },
  'connection-lost': {
    Icon: WifiOff,
    title: 'Connection lost',
    description: 'Your guide is still generating in the background.',
    actionLabel: 'Retry Connection',
  },
};

export function EmptyState({ variant, onAction }: EmptyStateProps) {
  const { Icon, title, description, actionLabel } = variants[variant];

  return (
    <div className="flex flex-col items-center justify-center py-16 px-4 text-center">
      <div className="w-14 h-14 rounded-2xl bg-slate-100 flex items-center justify-center mb-4">
        <Icon size={24} className="text-slate-400" />
      </div>
      <h3 className="text-base font-semibold text-slate-900 mb-1">{title}</h3>
      <p className="text-sm text-slate-500 max-w-sm mb-5">{description}</p>
      {variant === 'connection-lost' && (
        <p className="text-xs text-slate-400 mb-4">Or check back in the History tab</p>
      )}
      {actionLabel && onAction && (
        <button
          onClick={onAction}
          className="bg-blue-600 text-white px-5 py-2 rounded-lg text-sm font-medium hover:bg-blue-700 transition-colors cursor-pointer"
        >
          {actionLabel}
        </button>
      )}
    </div>
  );
}
