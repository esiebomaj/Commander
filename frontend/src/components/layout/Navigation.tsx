import { useLocation, useNavigate } from 'react-router-dom'
import { Inbox, Plug } from 'lucide-react'

export function Navigation() {
  const location = useLocation()
  const navigate = useNavigate()
  
  const currentTab = location.pathname.substring(1) || 'actions'
  
  const tabs = [
    { value: 'actions', label: 'Actions', icon: Inbox },
    { value: 'integrations', label: 'Integrations', icon: Plug },
  ]
  
  return (
    <div className="h-11 border-b border-gray-200 bg-white px-6 flex items-center gap-6">
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
                ? 'border-black text-black' 
                : 'border-transparent text-gray-500 hover:text-black'
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
