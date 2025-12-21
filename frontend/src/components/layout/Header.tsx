import { useState, useRef, useEffect } from "react";
import { Bell, LogOut, User } from "lucide-react";
import { useTheme } from "@/hooks/useTheme";
import { useAuth } from "@/contexts/AuthContext";
import commanderLogo from "@/assets/logo-dark-transparent.png";
import commanderLogoWhite from "@/assets/logo-light-transparent.png";

interface HeaderProps {
  pendingCount: number;
}

export function Header({ pendingCount }: HeaderProps) {
  const { isDark } = useTheme();
  const { user, signOut } = useAuth();
  const [showDropdown, setShowDropdown] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  // Close dropdown when clicking outside
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setShowDropdown(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const handleSignOut = async () => {
    try {
      await signOut();
    } catch (error) {
      console.error("Failed to sign out:", error);
    }
  };

  // Get user initials for avatar fallback
  const getInitials = () => {
    if (user?.user_metadata?.full_name) {
      return user.user_metadata.full_name
        .split(" ")
        .map((n: string) => n[0])
        .join("")
        .toUpperCase()
        .slice(0, 2);
    }
    if (user?.email) {
      return user.email[0].toUpperCase();
    }
    return "U";
  };

  return (
    <header className="h-14 border-b border-border bg-card flex items-center px-6 sticky top-0 z-50">
      <div className="flex items-center gap-2">
        <div className="w-10 h-10 bg-foreground rounded-lg flex items-center justify-center">
          {isDark ? (
            <img
              src={commanderLogo}
              alt="Commander Logo"
              className="h-8 w-8 text-background"
            />
          ) : (
            <img
              src={commanderLogoWhite}
              alt="Commander Logo"
              className="h-8 w-8 text-background"
            />
          )}
        </div>
        <span className="text-lg font-semibold tracking-tight text-foreground">
          Commander
        </span>
      </div>

      <div className="ml-auto flex items-center gap-2">
        {/* Notification Bell */}
        <button className="relative w-9 h-9 flex items-center justify-center rounded-lg hover:bg-accent transition-colors">
          <Bell className="h-[18px] w-[18px] text-muted-foreground" />
          {pendingCount > 0 && (
            <span className="absolute top-1 right-1 w-5 h-5 bg-red-500 text-white text-[10px] font-medium rounded-full flex items-center justify-center">
              {pendingCount > 9 ? "9+" : pendingCount}
            </span>
          )}
        </button>

        {/* User Menu */}
        <div className="relative" ref={dropdownRef}>
          <button
            onClick={() => setShowDropdown(!showDropdown)}
            className="w-9 h-9 rounded-full bg-accent flex items-center justify-center overflow-hidden hover:ring-2 hover:ring-primary/20 transition-all"
          >
            {user?.user_metadata?.avatar_url ? (
              <img
                src={user.user_metadata.avatar_url}
                alt="User avatar"
                className="w-full h-full object-cover"
              />
            ) : (
              <span className="text-sm font-medium text-foreground">
                {getInitials()}
              </span>
            )}
          </button>

          {/* Dropdown Menu */}
          {showDropdown && (
            <div className="absolute right-0 mt-2 w-64 bg-card border border-border rounded-lg shadow-lg py-2 z-50">
              {/* User Info */}
              <div className="px-4 py-3 border-b border-border">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-full bg-accent flex items-center justify-center overflow-hidden">
                    {user?.user_metadata?.avatar_url ? (
                      <img
                        src={user.user_metadata.avatar_url}
                        alt="User avatar"
                        className="w-full h-full object-cover"
                      />
                    ) : (
                      <User className="h-5 w-5 text-muted-foreground" />
                    )}
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-foreground truncate">
                      {user?.user_metadata?.full_name || "User"}
                    </p>
                    <p className="text-xs text-muted-foreground truncate">
                      {user?.email}
                    </p>
                  </div>
                </div>
              </div>

              {/* Sign Out Button */}
              <button
                onClick={handleSignOut}
                className="w-full px-4 py-2 text-left text-sm text-foreground hover:bg-accent flex items-center gap-2 transition-colors"
              >
                <LogOut className="h-4 w-4" />
                Sign out
              </button>
            </div>
          )}
        </div>
      </div>
    </header>
  );
}
