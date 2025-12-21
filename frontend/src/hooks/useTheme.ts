import { createContext, useContext, useState, useEffect, useCallback, type ReactNode, createElement } from 'react'

export type Theme = 'light' | 'dark' | 'system'

const THEME_KEY = 'commander-theme'

/**
 * Get the system's preferred color scheme
 */
function getSystemTheme(): 'light' | 'dark' {
  if (typeof window === 'undefined') return 'light'
  return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
}

/**
 * Get the stored theme preference or default to system
 */
function getStoredTheme(): Theme {
  if (typeof window === 'undefined') return 'system'
  const stored = localStorage.getItem(THEME_KEY)
  if (stored === 'light' || stored === 'dark' || stored === 'system') {
    return stored
  }
  return 'system'
}

/**
 * Apply the theme to the document
 */
function applyTheme(theme: Theme) {
  const root = document.documentElement
  const effectiveTheme = theme === 'system' ? getSystemTheme() : theme
  
  if (effectiveTheme === 'dark') {
    root.classList.add('dark')
  } else {
    root.classList.remove('dark')
  }
}

type ThemeContextType = {
  theme: Theme
  resolvedTheme: 'light' | 'dark'
  setTheme: (theme: Theme) => void
  isDark: boolean
}

const ThemeContext = createContext<ThemeContextType | undefined>(undefined)

/**
 * Theme Provider Component
 */
export function ThemeProvider({ children }: { children: ReactNode }) {
  const [theme, setThemeState] = useState<Theme>(getStoredTheme)
  const [resolvedTheme, setResolvedTheme] = useState<'light' | 'dark'>(
    () => theme === 'system' ? getSystemTheme() : theme
  )
  
  // Apply theme on mount and when it changes
  useEffect(() => {
    applyTheme(theme)
    setResolvedTheme(theme === 'system' ? getSystemTheme() : theme)
  }, [theme])
  
  // Listen for system theme changes
  useEffect(() => {
    const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)')
    
    const handleChange = () => {
      if (theme === 'system') {
        applyTheme('system')
        setResolvedTheme(getSystemTheme())
      }
    }
    
    mediaQuery.addEventListener('change', handleChange)
    return () => mediaQuery.removeEventListener('change', handleChange)
  }, [theme])
  
  const setTheme = useCallback((newTheme: Theme) => {
    localStorage.setItem(THEME_KEY, newTheme)
    setThemeState(newTheme)
  }, [])
  
  const value = {
    theme,
    resolvedTheme,
    setTheme,
    isDark: resolvedTheme === 'dark',
  }
  
  return createElement(ThemeContext.Provider, { value }, children)
}

/**
 * Hook to access theme state
 */
export function useTheme() {
  const context = useContext(ThemeContext)
  if (context === undefined) {
    throw new Error('useTheme must be used within a ThemeProvider')
  }
  return context
}

