import { Bell, Command } from 'lucide-react'

interface HeaderProps {
  pendingCount: number
}

export function Header({ pendingCount }: HeaderProps) {
  return (
    <header className="h-14 border-b border-gray-200 bg-white flex items-center px-6 sticky top-0 z-50">
      <div className="flex items-center gap-2">
        <div className="w-8 h-8 bg-black rounded-lg flex items-center justify-center">
          <Command className="h-4 w-4 text-white" />
        </div>
        <span className="text-lg font-semibold tracking-tight">Commander</span>
      </div>
      
      <div className="ml-auto flex items-center gap-2">
        <button className="relative w-9 h-9 flex items-center justify-center rounded-lg hover:bg-gray-100 transition-colors">
          <Bell className="h-[18px] w-[18px] text-gray-600" />
          {pendingCount > 0 && (
            <span className="absolute top-1 right-1 w-5 h-5 bg-red-500 text-white text-[10px] font-medium rounded-full flex items-center justify-center">
              {pendingCount > 9 ? '9+' : pendingCount}
            </span>
          )}
        </button>
      </div>
    </header>
  )
}
