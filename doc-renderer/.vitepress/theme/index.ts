import type { Theme } from 'vitepress'
import DefaultTheme from 'vitepress/theme'
import { enhanceApp } from './app'
import './style.css'
import './presets/brief.css'
import './presets/editorial.css'

export default {
  extends: DefaultTheme,
  enhanceApp,
} satisfies Theme
