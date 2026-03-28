// with polyfills
import 'core-js/stable'
import 'regenerator-runtime/runtime'

import Vue from 'vue'
import App from './App.vue'
import router from './router'
import store from './store/'
import i18n from './locales'
import request, { VueAxios, setDesktopApiPort } from './utils/request'
import ProLayout, { PageHeaderWrapper } from '@ant-design-vue/pro-layout'
import themePluginConfig from '../config/themePluginConfig'

import bootstrap from './core/bootstrap'
import './core/lazy_use'
import './permission'
import './utils/filter'
import './global.less'

Vue.config.productionTip = false

if (typeof window !== 'undefined') {
  const ignoreResizeObserverError = (e) => {
    const msg = (e && (e.reason && e.reason.message || e.message)) || ''
    if (msg.includes('ResizeObserver loop') || msg.includes('ResizeObserver loop limit exceeded')) {
      e.preventDefault && e.preventDefault()
      e.stopImmediatePropagation && e.stopImmediatePropagation()
      return false
    }
  }
  window.addEventListener('error', ignoreResizeObserverError)
  window.addEventListener('unhandledrejection', ignoreResizeObserverError)
}

Vue.use(VueAxios)
Vue.component('pro-layout', ProLayout)
Vue.component('page-container', PageHeaderWrapper)
Vue.component('page-header-wrapper', PageHeaderWrapper)

window.umi_plugin_ant_themeVar = themePluginConfig.theme

const shouldBootstrapDesktopRuntime = typeof window !== 'undefined' && !!(
  window.__TAURI__ ||
  window.__TAURI_IPC__ ||
  window.__TAURI_INTERNALS__
)

if (shouldBootstrapDesktopRuntime) {
  window.__ZHIYIQUANT_DESKTOP_RUNTIME__ = true
  window.__ZHIYIQUANT_RUNTIME_READY__ = false
}

function sleep (ms) {
  return new Promise(resolve => setTimeout(resolve, ms))
}

function emitDesktopRuntimeReady (ready) {
  if (typeof window === 'undefined') {
    return
  }

  window.__ZHIYIQUANT_RUNTIME_READY__ = !!ready
  window.dispatchEvent(new CustomEvent('zhiyiquant:runtime-ready', {
    detail: {
      ready: !!ready,
      baseURL: request.defaults.baseURL || window.__ZHIYIQUANT_API_BASE_URL__ || ''
    }
  }))
}

async function waitForDesktopBackend (baseURL) {
  if (!baseURL || typeof fetch === 'undefined') {
    return false
  }

  const healthCandidates = [
    `${baseURL}api/health`,
    `${baseURL}health`
  ]
  const deadline = Date.now() + 20000

  while (Date.now() < deadline) {
    for (const url of healthCandidates) {
      try {
        const response = await fetch(`${url}?_t=${Date.now()}`, { cache: 'no-store' })
        if (response.ok) {
          return true
        }
      } catch (e) {}
    }
    await sleep(250)
  }

  return false
}

async function initializeDesktopRuntime () {
  if (typeof window === 'undefined') {
    return true
  }

  window.__ZHIYIQUANT_RUNTIME_READY__ = true

  try {
    const [{ listen }, { invoke }] = await Promise.all([
      import('@tauri-apps/api/event'),
      import('@tauri-apps/api/core')
    ])

    window.__ZHIYIQUANT_DESKTOP_RUNTIME__ = true
    window.__ZHIYIQUANT_RUNTIME_READY__ = false

    await listen('zhiyiquant:backend-port', (event) => {
      if (event && event.payload) {
        setDesktopApiPort(event.payload)
      }
    })

    for (let attempt = 0; attempt < 40 && !window.__ZHIYIQUANT_API_PORT__; attempt++) {
      const port = await invoke('get_backend_port').catch(() => null)
      if (port) {
        setDesktopApiPort(port)
        break
      }
      await sleep(150)
    }

    const ready = await waitForDesktopBackend(request.defaults.baseURL || window.__ZHIYIQUANT_API_BASE_URL__)
    emitDesktopRuntimeReady(ready)
    return ready
  } catch (e) {
    window.__ZHIYIQUANT_DESKTOP_RUNTIME__ = false
    emitDesktopRuntimeReady(true)
    return true
  }
}

async function startApp () {
  new Vue({
    router,
    store,
    i18n,
    created: bootstrap,
    render: h => h(App)
  }).$mount('#app')

  initializeDesktopRuntime().catch(() => {})
}

startApp()
