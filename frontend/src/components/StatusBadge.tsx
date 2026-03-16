import { cn } from '@/lib/utils';

interface StatusBadgeProps {
  status: string;
  className?: string;
}

const statusConfig: Record<string, { label: string; className: string }> = {
  DRAFT: { label: 'Draft', className: 'bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-300' },
  SUBMITTED: { label: 'Submitted', className: 'bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-300' },
  APPROVED: { label: 'Approved', className: 'bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-300' },
  RETURNED_FOR_MODIFICATION: { label: 'Returned', className: 'bg-orange-100 text-orange-700 dark:bg-orange-900 dark:text-orange-300' },
};

export default function StatusBadge({ status, className }: StatusBadgeProps) {
  const config = statusConfig[status] || { label: status, className: 'bg-gray-100 text-gray-700' };

  return (
    <span
      className={cn(
        'inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium',
        config.className,
        className
      )}
    >
      {config.label}
    </span>
  );
}
