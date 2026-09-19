import { defineStore } from 'pinia'

export const useConfigStore = defineStore('config', {
  state: () => ({
    isDark: false
  }),
  actions: {
    toggleTheme(dark: boolean) {
      this.isDark = dark
    }
  }
})
