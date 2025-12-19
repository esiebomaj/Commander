import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { Layout } from './components/layout/Layout'
import { ActionsPage } from './pages/Actions'
import { IntegrationsPage } from './pages/Integrations'
import { SettingsPage } from './pages/Settings'
import { Toaster } from './components/ui/toaster'

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Layout />}>
          <Route index element={<Navigate to="/actions" replace />} />
          <Route path="actions" element={<ActionsPage />} />
          <Route path="integrations" element={<IntegrationsPage />} />
          <Route path="settings" element={<SettingsPage />} />
        </Route>
      </Routes>
      <Toaster />
    </BrowserRouter>
  )
}

export default App
