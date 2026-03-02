import { Link, useLocation } from 'react-router-dom';
import { BookOpen } from 'lucide-react';
import { APP_NAME, ROUTES } from '../../lib/constants';

export function Header() {
  const location = useLocation();

  const isActive = (path: string) => {
    if (path === '/') return location.pathname === '/';
    return location.pathname.startsWith(path);
  };

  return (
    <header className="sticky top-0 z-40 border-b border-border/60 bg-background/80 backdrop-blur-xl">
      <div className="mx-auto max-w-screen-2xl px-6">
        <div className="flex h-14 items-center justify-between">
          {/* Logo */}
          <Link to={ROUTES.HOME} className="flex items-center gap-2.5 group">
            <div className="relative flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-br from-amber-500 to-amber-700 shadow-md shadow-amber-900/20 transition-shadow group-hover:shadow-amber-800/30">
              <svg viewBox="0 0 24 24" fill="none" className="h-4 w-4 text-amber-50" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M17 3a2.85 2.83 0 1 1 4 4L7.5 20.5 2 22l1.5-5.5Z" />
                <path d="m15 5 4 4" />
              </svg>
            </div>
            <span className="font-display text-lg font-semibold tracking-tight text-foreground">
              {APP_NAME}
            </span>
          </Link>

          {/* Navigation */}
          <nav className="flex items-center gap-1">
            <Link
              to={ROUTES.PROJECTS}
              className={`relative px-3.5 py-1.5 text-sm font-medium rounded-md transition-colors
                ${isActive('/projects') || isActive('/')
                  ? 'text-foreground bg-muted/60'
                  : 'text-muted-foreground hover:text-foreground hover:bg-muted/40'
                }`}
            >
              Projects
            </Link>
            <Link
              to={ROUTES.BOOKS}
              className={`relative flex items-center gap-1.5 px-3.5 py-1.5 text-sm font-medium rounded-md transition-colors
                ${isActive('/books')
                  ? 'text-foreground bg-muted/60'
                  : 'text-muted-foreground hover:text-foreground hover:bg-muted/40'
                }`}
            >
              <BookOpen className="h-3.5 w-3.5" />
              Books
            </Link>
          </nav>
        </div>
      </div>
    </header>
  );
}
