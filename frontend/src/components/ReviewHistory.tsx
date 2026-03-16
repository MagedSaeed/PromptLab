import { CheckCircle2, RotateCcw, Clock } from 'lucide-react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Separator } from '@/components/ui/separator';
import type { ReviewAction } from '@/types';

interface ReviewHistoryProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  actions: ReviewAction[];
}

function formatDate(dateStr: string): string {
  const date = new Date(dateStr);
  return date.toLocaleDateString(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

function DecisionBadge({ decision, display }: { decision: string | null; display: string }) {
  if (!decision) {
    return (
      <Badge variant="outline" className="gap-1">
        <Clock className="h-3 w-3" />
        {display || 'Submitted'}
      </Badge>
    );
  }

  const lower = decision.toLowerCase();

  if (lower === 'approved' || lower === 'approve') {
    return (
      <Badge className="gap-1 bg-green-100 text-green-800 hover:bg-green-100 dark:bg-green-900/30 dark:text-green-300">
        <CheckCircle2 className="h-3 w-3" />
        {display || 'Approved'}
      </Badge>
    );
  }

  if (lower.includes('return')) {
    return (
      <Badge className="gap-1 bg-amber-100 text-amber-800 hover:bg-amber-100 dark:bg-amber-900/30 dark:text-amber-300">
        <RotateCcw className="h-3 w-3" />
        {display || 'Returned'}
      </Badge>
    );
  }

  return (
    <Badge variant="secondary" className="gap-1">
      {display || decision}
    </Badge>
  );
}

export default function ReviewHistory({ open, onOpenChange, actions }: ReviewHistoryProps) {
  const sortedActions = [...actions].sort(
    (a, b) => new Date(b.taken_on).getTime() - new Date(a.taken_on).getTime()
  );

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>Review History</DialogTitle>
          <DialogDescription>
            {sortedActions.length === 0
              ? 'No review actions have been recorded yet.'
              : `${sortedActions.length} review action${sortedActions.length !== 1 ? 's' : ''}`}
          </DialogDescription>
        </DialogHeader>

        {sortedActions.length > 0 && (
          <ScrollArea className="max-h-[400px] pr-4">
            <div className="space-y-1">
              {sortedActions.map((action, index) => (
                <div key={action.id}>
                  <div className="py-3 space-y-2">
                    <div className="flex items-center justify-between gap-2">
                      <span className="text-sm font-medium">
                        {action.submitter.username}
                      </span>
                      <DecisionBadge
                        decision={action.submitter_decision}
                        display={action.submitter_decision_display}
                      />
                    </div>

                    {action.submitter_comment && (
                      <p className="text-sm text-muted-foreground bg-muted/50 rounded-md px-3 py-2">
                        {action.submitter_comment}
                      </p>
                    )}

                    <p className="text-xs text-muted-foreground">{formatDate(action.taken_on)}</p>
                  </div>

                  {index < sortedActions.length - 1 && <Separator />}
                </div>
              ))}
            </div>
          </ScrollArea>
        )}
      </DialogContent>
    </Dialog>
  );
}
