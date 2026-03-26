import router, {
  resetRouter
} from './router'
import store from './store'
import storage from 'store'
import NProgress from 'nprogress' // progress bar
import '@/components/NProgress/nprogress.less' // progress bar custom style
import {
  setDocumentTitle,
  domTitle
} from '@/utils/domUtil'
import {
  ACCESS_TOKEN
} from '@/store/mutation-types'
import {
  i18nRender
} from '@/locales'

NProgress.configure({
  showSpinner: false
}) // NProgress Configuration

const allowList = ['login'] // no redirect allowList
const loginRoutePath = '/user/login'
const defaultRoutePath = '/dashboard'

router.beforeEach((to, from, next) => {
  NProgress.start() // start progress bar
  to.meta && typeof to.meta.title !== 'undefined' && setDocumentTitle(`${i18nRender(to.meta.title)} - ${domTitle}`)

  // Check whether we have a token (local-only auth).
  // 处理 token 可能是字符串或对象的情况
  let token = storage.get(ACCESS_TOKEN)
  if (token && typeof token !== 'string') {
    token = token.token || token.value || (typeof token === 'object' ? null : token)
  }
  token = typeof token === 'string' ? token : null

  if (token) {
    // 有 token，允许访问所有页面
    // 如果访问登录页，跳转到默认页面
    if (to.path === loginRoutePath) {
      next({ path: defaultRoutePath })
      NProgress.done()
    } else {
      // 检查用户信息是否已加载
      if (store.getters.roles.length === 0) {
        store.dispatch('GetInfo')
          .then(res => {
            // 拉取用户信息成功
            // const roles = res && res.role
            // 生成路由
            store.dispatch('GenerateRoutes', { token }).then(() => {
              // 动态添加可访问路由表
              resetRouter() // 重置路由
              store.getters.addRouters.forEach(r => {
                router.addRoute(r)
              })
              // 请求带有 redirect 重定向时，登录自动重定向到该地址
              const redirect = decodeURIComponent(from.query.redirect || to.path)
              if (to.path === redirect) {
                // hack方法 确保addRoutes已完成 ,set the replace: true so the navigation will not leave a history record
                next({ ...to, replace: true })
              } else {
                // 跳转到目的路由
                next({ path: redirect })
              }
            })
          })
          .catch((err) => {
            // If token is invalid/expired, clear local auth and redirect to login.
            const status = err && err.response && err.response.status
            if (status === 401) {
              store.dispatch('Logout').finally(() => {
                next({ path: loginRoutePath, query: { redirect: to.fullPath } })
                NProgress.done()
              })
              return
            }

            // Do NOT hard-logout on transient failures (backend down, proxy issue, etc).
            // Instead, degrade gracefully with a default role and continue.
            store.commit('SET_ROLES', [{ id: 'default', permissionList: [] }])
            store.dispatch('GenerateRoutes', { token }).then(() => {
              resetRouter()
              store.getters.addRouters.forEach(r => router.addRoute(r))
              next({ ...to, replace: true })
            }).catch(() => {
              next()
            })
          })
      } else {
        // 检查路由是否已初始化
        const addRouters = store.getters.addRouters
        // 如果路由未初始化，先初始化路由
        if (!addRouters || addRouters.length === 0) {
          store.dispatch('GenerateRoutes', { token }).then(() => {
            // 动态添加可访问路由表
            resetRouter() // 重置路由 防止退出重新登录或者 token 过期后页面未刷新，导致的路由重复添加
            store.getters.addRouters.forEach(r => {
              router.addRoute(r)
            })
            // 重新进入当前路由，避免首次刷新空白
            next({ ...to, replace: true })
          }).catch(() => {
            next()
          })
        } else {
          next()
        }
      }
    }
  } else {
    // 没有 token
    if (allowList.includes(to.name)) {
      // 在免登录名单，直接进入
      next()
    } else {
      // 跳转到登录页
      next({ path: loginRoutePath, query: { redirect: to.fullPath } })
      NProgress.done() // if current page is login will not trigger afterEach hook, so manually handle it
    }
  }
})

router.afterEach(() => {
  NProgress.done() // finish progress bar
})
