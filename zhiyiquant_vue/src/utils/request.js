import axios from 'axios'
import storage from 'store'
import notification from 'ant-design-vue/es/notification'
import { VueAxios } from './axios'
import { ACCESS_TOKEN, USER_INFO, USER_ROLES } from '@/store/mutation-types'

const LOCALE_KEY = 'lang'
let isRedirectingToLogin = false
let desktopApiReadyPromise = null

function sleep (ms) {
  return new Promise(resolve => setTimeout(resolve, ms))
}

function isTauriRuntime () {
  if (typeof window === 'undefined') {
    return false
  }

  return !!(
    window.__ZHIYIQUANT_DESKTOP_RUNTIME__ ||
    window.__TAURI__ ||
    window.__TAURI_IPC__ ||
    window.__TAURI_INTERNALS__
  )
}

function normalizeBaseURL (baseURL) {
  if (!baseURL) {
    return ''
  }

  const trimmed = String(baseURL).trim()
  if (!trimmed) {
    return ''
  }

  if (trimmed === '/api' || trimmed === '/api/') {
    return '/'
  }

  return trimmed
}

function resolveBaseURL () {
  if (typeof window !== 'undefined') {
    const injected = window.__ZHIYIQUANT_API_BASE_URL__
    if (typeof injected === 'string' && injected.trim()) {
      return injected.trim()
    }

    const port = Number(window.__ZHIYIQUANT_API_PORT__)
    if (port) {
      return `http://127.0.0.1:${port}/`
    }

    if (window.__ZHIYIQUANT_DESKTOP_RUNTIME__) {
      return ''
    }
  }

  return normalizeBaseURL(process.env.VUE_APP_API_BASE_URL || '/')
}

function buildDesktopBaseURL (port) {
  const normalizedPort = Number(port)
  if (!normalizedPort || Number.isNaN(normalizedPort)) {
    return ''
  }
  return `http://127.0.0.1:${normalizedPort}/`
}

function emitDesktopRuntimeReady (ready, baseURL = '') {
  if (typeof window === 'undefined') {
    return
  }

  window.__ZHIYIQUANT_RUNTIME_READY__ = !!ready
  window.dispatchEvent(new CustomEvent('zhiyiquant:runtime-ready', {
    detail: {
      ready: !!ready,
      baseURL
    }
  }))
}

async function waitForDesktopBackendHealth (baseURL, timeoutMs = 20000) {
  if (!baseURL || typeof fetch === 'undefined') {
    return false
  }

  const candidates = [
    `${baseURL}api/health`,
    `${baseURL}health`
  ]
  const deadline = Date.now() + timeoutMs

  while (Date.now() < deadline) {
    for (const url of candidates) {
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

async function ensureDesktopBaseURL () {
  if (!isTauriRuntime()) {
    return resolveBaseURL()
  }

  if (window.__ZHIYIQUANT_API_BASE_URL__ && window.__ZHIYIQUANT_RUNTIME_READY__) {
    return window.__ZHIYIQUANT_API_BASE_URL__
  }

  if (!desktopApiReadyPromise) {
    desktopApiReadyPromise = (async () => {
      let baseURL = window.__ZHIYIQUANT_API_BASE_URL__ || ''

      if (!baseURL) {
        try {
          const { invoke } = await import('@tauri-apps/api/core')
          const port = await invoke('get_backend_port').catch(() => null)
          if (port) {
            baseURL = setDesktopApiPort(port)
          }
        } catch (e) {}
      }

      baseURL = baseURL || resolveBaseURL()
      const ready = await waitForDesktopBackendHealth(baseURL)
      emitDesktopRuntimeReady(ready, baseURL)
      return baseURL
    })().finally(() => {
      desktopApiReadyPromise = null
    })
  }

  return desktopApiReadyPromise
}

function getToken () {
  const token = storage.get(ACCESS_TOKEN)
  if (typeof token === 'string') return token
  if (token && typeof token === 'object') return token.token || token.value || null
  return null
}

const request = axios.create({
  baseURL: resolveBaseURL() || '/',
  timeout: 30000
})

export const ANALYSIS_TIMEOUT = 180000

export function setDesktopApiPort (port) {
  const baseURL = buildDesktopBaseURL(port)
  if (!baseURL) {
    return ''
  }

  if (typeof window !== 'undefined') {
    window.__ZHIYIQUANT_API_PORT__ = Number(port)
    window.__ZHIYIQUANT_API_BASE_URL__ = baseURL
  }

  request.defaults.baseURL = baseURL
  return baseURL
}

const errorHandler = (error) => {
  if (error.response && error.response.status === 401 && !isRedirectingToLogin) {
    isRedirectingToLogin = true

    try {
      storage.remove(ACCESS_TOKEN)
      storage.remove(USER_INFO)
      storage.remove(USER_ROLES)
    } catch (e) {}

    notification.error({
      message: 'Unauthorized',
      description: error.response.data?.msg || 'Session expired. Please log in again.'
    })

    const curHash = window.location.hash || ''
    if (!curHash.includes('/user/login')) {
      const redirect = encodeURIComponent(curHash.replace('#', '') || '/')
      window.location.assign(`/#/user/login?redirect=${redirect}`)
    }
  }

  return Promise.reject(error)
}

request.interceptors.request.use(async config => {
  const resolvedBaseURL = isTauriRuntime()
    ? await ensureDesktopBaseURL()
    : resolveBaseURL()

  if (resolvedBaseURL) {
    config.baseURL = resolvedBaseURL
  }

  const token = getToken()
  const lang = storage.get(LOCALE_KEY) || 'en-US'

  config.headers['X-App-Lang'] = lang
  config.headers['Accept-Language'] = lang
  config.headers['Cache-Control'] = 'no-cache'
  config.headers.Pragma = 'no-cache'
  config.headers['If-Modified-Since'] = '0'

  if (token) {
    config.headers.Authorization = `Bearer ${token}`
    config.headers[ACCESS_TOKEN] = token
    config.headers.token = token
  }

  if ((config.method || 'get').toLowerCase() === 'get') {
    config.params = Object.assign({}, config.params || {}, { _t: Date.now() })
  }

  return config
}, errorHandler)

request.interceptors.response.use((response) => response.data, errorHandler)

const installer = {
  vm: {},
  install (Vue) {
    Vue.use(VueAxios, request)
  }
}

export default request

export {
  installer as VueAxios,
  request as axios
}
