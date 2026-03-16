import { Link } from 'react-router-dom';
import { ChevronRight } from 'lucide-react';
import type { ReactNode } from 'react';

interface Breadcrumb {
  label: string;
  href?: string;
  to?: string;
}

interface PageLayoutProps {
  title: string;
  breadcrumbs?: Breadcrumb[];
  actions?: ReactNode;
  children: ReactNode;
}

export default function PageLayout({ title, breadcrumbs, actions, children }: PageLayoutProps) {
  return (
    <div className="container mx-auto px-4 py-6">
      {/* Breadcrumbs */}
      {breadcrumbs && breadcrumbs.length > 0 && (
        <nav className="flex items-center space-x-1 text-sm text-muted-foreground mb-4">
          {breadcrumbs.map((crumb, index) => (
            <span key={index} className="flex items-center">
              {index > 0 && <ChevronRight className="h-3.5 w-3.5 mx-1" />}
              {(crumb.href || crumb.to) ? (
                <Link to={(crumb.href || crumb.to)!} className="hover:text-foreground transition-colors">
                  {crumb.label}
                </Link>
              ) : (
                <span className="text-foreground font-medium">{crumb.label}</span>
              )}
            </span>
          ))}
        </nav>
      )}

      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold tracking-tight">{title}</h1>
        {actions && <div className="flex items-center space-x-2">{actions}</div>}
      </div>

      {/* Content */}
      {children}
    </div>
  );
}
