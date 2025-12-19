import { Outlet } from 'react-router-dom'
import { Header } from './Header'
import { Navigation } from './Navigation'
import { useNewActions } from '@/hooks/useNewActions'

export function Layout() {
  const { pendingCount } = useNewActions()
  
  return (
    <div className="min-h-screen bg-background">
      <Header pendingCount={pendingCount} />
      <Navigation />
      <main className="max-w-5xl mx-auto px-6 py-8">
        <Outlet />
      </main>
    </div>
  )
}
