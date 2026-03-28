import router, { resetRouter } from './router'
import store from './store'
import storage from 'store'
import NProgress from 'nprogress'
import '@/components/NProgress/nprogress.less'
import { setDocumentTitle, domTitle } from '@/utils/domUtil'
import { ACCESS_TOKEN } from '@/store/mutation-types'
import { i18nRender } from '@/locales'

NProgress.configure({ showSpinner: false })

const loginRoutePath = '/user/login'
const defaultRoutePath = '/dashboard'

function getStoredToken () {
  const token = storage.get(ACCESS_TOKEN)
  if (typeof token === 'string') return token
  return token && token.token ? token.token : null
}

router.beforeEach((to, from, next) => {
  NProgress.start()

  if (to.meta && typeof to.meta.title !== 'undefined') {
    setDocumentTitle(`${i18nRender(to.meta.title)} - ${domTitle}`)
  }

  const token = getStoredToken()

  if (!token) {
    if (to.path === loginRoutePath) {
      next()
    } else {
      next({ path: loginRoutePath, query: { redirect: to.fullPath } })
      NProgress.done()
    }
    return
  }

  if (to.path === loginRoutePath) {
    next({ path: defaultRoutePath })
    NProgress.done()
    return
  }

  store.dispatch('GetInfo')
    .then(() => {
      store.dispatch('GenerateRoutes').then(() => {
        resetRouter()
        store.getters.addRouters.forEach(r => router.addRoute(r))
        next({ ...to, replace: true })
      }).catch(() => next())
    })
    .catch(() => {
      store.dispatch('Logout').finally(() => {
        next({ path: loginRoutePath, query: { redirect: to.fullPath } })
        NProgress.done()
      })
    })
})

router.afterEach(() => {
  NProgress.done()
})
