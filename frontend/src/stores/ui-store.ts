import { create } from 'zustand'
import { persist } from 'zustand/middleware'

interface UiState {
  activeNav: 'chat' | 'manage' | 'settings'
  sidePanelOpen: boolean
  theme: 'dark' | 'light'
  sidebarCollapsed: boolean
}

interface UiActions {
  setActiveNav: (nav: UiState['activeNav']) => void
  setSidePanelOpen: (open: boolean) => void
  toggleTheme: () => void
  setSidebarCollapsed: (collapsed: boolean) => void
}

export const useUiStore = create<UiState & UiActions>()(
  persist(
    (set) => ({
      activeNav: 'chat',
      sidePanelOpen: false,
      theme: 'dark',
      sidebarCollapsed: false,

      setActiveNav: (nav) => set({ activeNav: nav }),
      setSidePanelOpen: (open) => set({ sidePanelOpen: open }),
      toggleTheme: () =>
        set((state) => {
          const newTheme = state.theme === 'dark' ? 'light' : 'dark'
          // Apply theme class to document root
          document.documentElement.classList.toggle('dark', newTheme === 'dark')
          return { theme: newTheme }
        }),
      setSidebarCollapsed: (collapsed) => set({ sidebarCollapsed: collapsed }),
    }),
    {
      name: 'nextflow-theme',
      partialize: (state) => ({ theme: state.theme }),
    },
  ),
)
