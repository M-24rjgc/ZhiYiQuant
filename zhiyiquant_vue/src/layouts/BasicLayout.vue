<template>
  <div :class="['basic-layout-wrapper', settings.theme]">
    <pro-layout
      :menus="menus"
      :collapsed="collapsed"
      :mediaQuery="query"
      :isMobile="isMobile"
      :handleMediaQuery="handleMediaQuery"
      :handleCollapse="handleCollapse"
      :i18nRender="i18nRender"
      v-bind="settings"
    >
      <template #menuHeaderRender>
        <div class="menu-brand">
          <img src="~@/assets/brand-mark.png" alt="智弈量化" class="brand-mark">
          <h1>{{ title }}</h1>
        </div>
      </template>

      <template #headerContentRender>
        <div class="header-actions">
          <a-tooltip title="刷新当前页面">
            <a-icon type="reload" @click="handleRefresh" />
          </a-tooltip>
        </div>
      </template>

      <setting-drawer ref="settingDrawer" :settings="settings" @change="handleSettingChange">
        <div style="margin: 12px 0;">
          桌面偏好
        </div>
      </setting-drawer>

      <template #rightContentRender>
        <right-content :top-menu="settings.layout === 'topmenu'" :is-mobile="isMobile" :theme="settings.theme" />
      </template>

      <template #footerRender>
        <div style="display: none;"></div>
      </template>

      <router-view :key="refreshKey" />
    </pro-layout>

    <div class="custom-menu-footer" :class="{ collapsed }">
      <div v-if="!collapsed" class="menu-footer-content">
        <div class="footer-section">
          <div class="section-title">桌面本地模式</div>
          <div class="section-links">策略研究 · AI 分析 · 交易执行</div>
        </div>
        <div class="footer-section copyright">
          © 2026 智弈量化
        </div>
        <div class="footer-section version">
          V1.0.0
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { updateTheme } from '@/components/SettingDrawer/settingConfig'
import { i18nRender } from '@/locales'
import { mapState } from 'vuex'
import {
  CONTENT_WIDTH_TYPE,
  SIDEBAR_TYPE,
  TOGGLE_MOBILE_TYPE,
  TOGGLE_NAV_THEME,
  TOGGLE_LAYOUT,
  TOGGLE_FIXED_HEADER,
  TOGGLE_FIXED_SIDEBAR,
  TOGGLE_CONTENT_WIDTH,
  TOGGLE_HIDE_HEADER,
  TOGGLE_COLOR,
  TOGGLE_WEAK,
  TOGGLE_MULTI_TAB
} from '@/store/mutation-types'

import defaultSettings from '@/config/defaultSettings'
import RightContent from '@/components/GlobalHeader/RightContent'
import SettingDrawer from '@/components/SettingDrawer/SettingDrawer'

export default {
  name: 'BasicLayout',
  components: {
    SettingDrawer,
    RightContent
  },
  data () {
    return {
      collapsed: false,
      title: defaultSettings.title,
      settings: {
        layout: defaultSettings.layout,
        contentWidth: defaultSettings.layout === 'sidemenu' ? CONTENT_WIDTH_TYPE.Fluid : defaultSettings.contentWidth,
        theme: defaultSettings.navTheme,
        primaryColor: defaultSettings.primaryColor,
        fixedHeader: defaultSettings.fixedHeader,
        fixSiderbar: defaultSettings.fixSiderbar,
        colorWeak: defaultSettings.colorWeak,
        hideHintAlert: false,
        hideCopyButton: false
      },
      query: {},
      isMobile: false,
      refreshKey: 0,
      isInitialThemeColorLoad: true
    }
  },
  computed: {
    ...mapState({
      mainMenu: state => state.permission.addRouters
    }),
    menus () {
      const routes = this.mainMenu.find(item => item.path === '/')
      return (routes && routes.children) || []
    }
  },
  created () {
    this.settings.theme = this.$store.state.app.theme
    this.settings.primaryColor = this.$store.state.app.color || defaultSettings.primaryColor

    this.$watch('collapsed', () => {
      this.$store.commit(SIDEBAR_TYPE, this.collapsed)
    })
    this.$watch('isMobile', () => {
      this.$store.commit(TOGGLE_MOBILE_TYPE, this.isMobile)
    })
    this.$watch('$store.state.app.theme', (val) => {
      this.settings.theme = val
      if (val === 'dark' || val === 'realdark') {
        document.body.classList.add('dark')
        document.body.classList.remove('light')
      } else {
        document.body.classList.remove('dark')
        document.body.classList.add('light')
      }
    }, { immediate: true })
    this.$watch('$store.state.app.color', (val) => {
      if (val) {
        this.settings.primaryColor = val
        if (process.env.NODE_ENV !== 'production' || process.env.VUE_APP_PREVIEW === 'true') {
          updateTheme(val, this.isInitialThemeColorLoad)
          if (this.isInitialThemeColorLoad) {
            this.isInitialThemeColorLoad = false
          }
        }
      }
    }, { immediate: true })
  },
  methods: {
    i18nRender,
    handleMediaQuery (val) {
      this.query = val
      if (val['screen-xs']) {
        this.isMobile = true
        this.collapsed = false
      } else {
        this.isMobile = false
      }
    },
    handleCollapse (val) {
      this.collapsed = val
    },
    handleRefresh () {
      this.refreshKey += 1
    },
    handleSettingChange ({ type, value }) {
      switch (type) {
        case 'theme':
          this.settings.theme = value
          this.$store.commit(TOGGLE_NAV_THEME, value)
          break
        case 'layout':
          this.settings.layout = value
          this.$store.commit(TOGGLE_LAYOUT, value)
          break
        case 'contentWidth':
          this.settings.contentWidth = value
          this.$store.commit(TOGGLE_CONTENT_WIDTH, value)
          break
        case 'fixedHeader':
          this.settings.fixedHeader = value
          this.$store.commit(TOGGLE_FIXED_HEADER, value)
          break
        case 'fixSiderbar':
          this.settings.fixSiderbar = value
          this.$store.commit(TOGGLE_FIXED_SIDEBAR, value)
          break
        case 'color':
          this.settings.primaryColor = value
          this.$store.commit(TOGGLE_COLOR, value)
          break
        case 'weak':
          this.settings.colorWeak = value
          this.$store.commit(TOGGLE_WEAK, value)
          break
        case 'multiTab':
          this.$store.commit(TOGGLE_MULTI_TAB, value)
          break
        case 'hideHeader':
          this.$store.commit(TOGGLE_HIDE_HEADER, value)
          break
        default:
          break
      }
    }
  }
}
</script>

<style lang="less" scoped>
.menu-brand {
  display: flex;
  align-items: center;
  gap: 10px;
}

.brand-mark {
  width: 28px;
  height: 28px;
}

.menu-brand h1 {
  margin: 0;
}

.header-actions {
  display: flex;
  align-items: center;

  .anticon {
    font-size: 18px;
    cursor: pointer;
  }
}

.custom-menu-footer {
  position: fixed;
  left: 0;
  bottom: 0;
  width: 256px;
  padding: 12px 16px 18px;
  background: rgba(255, 255, 255, 0.92);
  border-top: 1px solid rgba(0, 0, 0, 0.06);
  z-index: 8;

  &.collapsed {
    width: 80px;
  }
}

.menu-footer-content {
  display: flex;
  flex-direction: column;
  gap: 8px;
  font-size: 12px;
  color: #5e737d;
}

.section-title {
  font-weight: 600;
  color: #16323b;
}

.section-links {
  line-height: 1.5;
}

.version {
  color: #8aa0aa;
}

@media (max-width: 991px) {
  .custom-menu-footer {
    display: none;
  }
}
</style>
