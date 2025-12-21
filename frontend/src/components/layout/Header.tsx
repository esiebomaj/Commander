import { Bell } from "lucide-react";
import { useTheme } from "@/hooks/useTheme";
import commanderLogo from "@/assets/logo-dark-transparent.png";
import commanderLogoWhite from "@/assets/logo-light-transparent.png";

interface HeaderProps {
  pendingCount: number;
}

export function Header({ pendingCount }: HeaderProps) {
  const { isDark } = useTheme();
  return (
    <header className="h-14 border-b border-border bg-card flex items-center px-6 sticky top-0 z-50">
      <div className="flex items-center gap-2">
        <div className="w-8 h-8 bg-foreground rounded-lg flex items-center justify-center">
          {isDark ? (
            <img
              src={commanderLogo}
              alt="Commander Logo"
              className="h-4 w-4 text-background"
            />
          ) : (
            <img
              src={commanderLogoWhite}
              alt="Commander Logo"
              className="h-4 w-4 text-background"
            />
          )}
        </div>
        <span className="text-lg font-semibold tracking-tight text-foreground">
          Commander
        </span>
      </div>

      <div className="ml-auto flex items-center gap-2">
        <button className="relative w-9 h-9 flex items-center justify-center rounded-lg hover:bg-accent transition-colors">
          <Bell className="h-[18px] w-[18px] text-muted-foreground" />
          {pendingCount > 0 && (
            <span className="absolute top-1 right-1 w-5 h-5 bg-red-500 text-white text-[10px] font-medium rounded-full flex items-center justify-center">
              {pendingCount > 9 ? "9+" : pendingCount}
            </span>
          )}
        </button>
      </div>
    </header>
  );
}
