import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '@/contexts/AuthContext';
import { useTheme } from '@/contexts/ThemeContext';
import { Sun, Moon, Monitor, Menu, LogOut, Settings, User, FolderOpen, FileText, Database } from 'lucide-react';
import { useState } from 'react';

export default function Navbar() {
  const { user, isAuthenticated, logout } = useAuth();
  const { theme, setTheme } = useTheme();
  const navigate = useNavigate();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const themeIcon = theme === 'dark' ? <Moon className="h-4 w-4" /> : theme === 'light' ? <Sun className="h-4 w-4" /> : <Monitor className="h-4 w-4" />;

  const cycleTheme = () => {
    const themes: ('light' | 'dark' | 'system')[] = ['light', 'dark', 'system'];
    const currentIndex = themes.indexOf(theme);
    setTheme(themes[(currentIndex + 1) % themes.length]);
  };

  return (
    <nav className="sticky top-0 z-50 border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
      <div className="container mx-auto px-4">
        <div className="flex h-14 items-center justify-between">
          {/* Logo */}
          <Link to="/" className="flex items-center space-x-2 font-bold text-xl">
            <span className="bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">
              PromptLab
            </span>
          </Link>

          {/* Desktop Navigation */}
          {isAuthenticated && (
            <div className="hidden md:flex items-center space-x-6">
              <Link to="/app/projects" className="flex items-center space-x-1 text-sm text-muted-foreground hover:text-foreground transition-colors">
                <FolderOpen className="h-4 w-4" />
                <span>Projects</span>
              </Link>
              <Link to="/app/my-prompts" className="flex items-center space-x-1 text-sm text-muted-foreground hover:text-foreground transition-colors">
                <FileText className="h-4 w-4" />
                <span>My Prompts</span>
              </Link>
              <Link to="/app/my-datasets" className="flex items-center space-x-1 text-sm text-muted-foreground hover:text-foreground transition-colors">
                <Database className="h-4 w-4" />
                <span>My Datasets</span>
              </Link>
              {user?.is_staff && (
                <Link to="/app/hf-sync" className="text-sm text-muted-foreground hover:text-foreground transition-colors">
                  HF Sync
                </Link>
              )}
            </div>
          )}

          {/* Right side */}
          <div className="flex items-center space-x-3">
            <button
              onClick={cycleTheme}
              className="rounded-md p-2 hover:bg-accent transition-colors"
              title={`Theme: ${theme}`}
            >
              {themeIcon}
            </button>

            {isAuthenticated && user ? (
              <div className="relative group">
                <button className="flex items-center space-x-2 rounded-md px-3 py-1.5 hover:bg-accent transition-colors">
                  <div className="h-7 w-7 rounded-full bg-primary/10 flex items-center justify-center">
                    <User className="h-4 w-4 text-primary" />
                  </div>
                  <span className="hidden sm:inline text-sm font-medium">{user.username}</span>
                </button>
                <div className="absolute right-0 mt-1 w-48 rounded-md border bg-popover shadow-lg opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all duration-200">
                  <div className="p-1">
                    <button
                      onClick={() => navigate('/app/settings')}
                      className="flex w-full items-center space-x-2 rounded-sm px-3 py-2 text-sm hover:bg-accent transition-colors"
                    >
                      <Settings className="h-4 w-4" />
                      <span>Settings</span>
                    </button>
                    <button
                      onClick={logout}
                      className="flex w-full items-center space-x-2 rounded-sm px-3 py-2 text-sm text-red-600 hover:bg-accent transition-colors"
                    >
                      <LogOut className="h-4 w-4" />
                      <span>Logout</span>
                    </button>
                  </div>
                </div>
              </div>
            ) : (
              <Link
                to="/app/login"
                className="rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 transition-colors"
              >
                Sign In
              </Link>
            )}

            {/* Mobile menu button */}
            {isAuthenticated && (
              <button
                className="md:hidden rounded-md p-2 hover:bg-accent"
                onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              >
                <Menu className="h-5 w-5" />
              </button>
            )}
          </div>
        </div>

        {/* Mobile menu */}
        {mobileMenuOpen && isAuthenticated && (
          <div className="md:hidden border-t py-2 space-y-1">
            <Link to="/app/projects" className="block px-3 py-2 text-sm rounded-md hover:bg-accent" onClick={() => setMobileMenuOpen(false)}>Projects</Link>
            <Link to="/app/my-prompts" className="block px-3 py-2 text-sm rounded-md hover:bg-accent" onClick={() => setMobileMenuOpen(false)}>My Prompts</Link>
            <Link to="/app/my-datasets" className="block px-3 py-2 text-sm rounded-md hover:bg-accent" onClick={() => setMobileMenuOpen(false)}>My Datasets</Link>
            {user?.is_staff && (
              <Link to="/app/hf-sync" className="block px-3 py-2 text-sm rounded-md hover:bg-accent" onClick={() => setMobileMenuOpen(false)}>HF Sync</Link>
            )}
          </div>
        )}
      </div>
    </nav>
  );
}
