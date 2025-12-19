import { useLocation, useNavigate } from 'react-router-dom'
import { Inbox, Plug, Settings } from 'lucide-react'

export function Navigation() {
  const location = useLocation()
  const navigate = useNavigate()
  
  const currentTab = location.pathname.substring(1) || 'actions'
  
  const tabs = [
    { value: 'actions', label: 'Actions', icon: Inbox },
    { value: 'integrations', label: 'Integrations', icon: Plug },
    { value: 'settings', label: 'Settings', icon: Settings },
  ]
  
  return (
    <div className="h-11 border-b border-border bg-card px-6 flex items-center gap-6">
      {tabs.map((tab) => {
        const Icon = tab.icon
        const isActive = currentTab === tab.value
        return (
          <button
            key={tab.value}
            onClick={() => navigate(`/${tab.value}`)}
            className={`
              flex items-center gap-2 h-full text-sm font-medium transition-colors
              border-b-2 -mb-[1px]
              ${isActive 
                ? 'border-foreground text-foreground' 
                : 'border-transparent text-muted-foreground hover:text-foreground'
              }
            `}
          >
            <Icon className="h-4 w-4" />
            {tab.label}
          </button>
        )
      })}
    </div>
  )
}
