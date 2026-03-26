import { asyncRouterMap, constantRouterMap } from '@/config/router.config'
import cloneDeep from 'lodash.clonedeep'

/**
 * 单账户多角色时，使用该方法可过滤角色不存在的菜单
 *
 * @param roles
 * @param route
 * @returns {*}
 */
// eslint-disable-next-line
function hasRole(roles, route) {
  if (route.meta && route.meta.roles) {
    return route.meta.roles.includes(roles.id)
  } else {
    return true
  }
}

function filterAsyncRouter (routerMap, role) {
  // 不进行权限过滤，直接返回所有路由（后端会验证token）
  return routerMap.map(route => {
    if (route.children && route.children.length) {
      route.children = filterAsyncRouter(route.children, role)
    }
    return route
  })
}

const permission = {
  state: {
    routers: constantRouterMap,
    addRouters: []
  },
  mutations: {
    SET_ROUTERS: (state, routers) => {
      state.addRouters = routers
      state.routers = constantRouterMap.concat(routers)
    }
  },
  actions: {
    GenerateRoutes ({ commit }, data) {
      return new Promise(resolve => {
        const routerMap = cloneDeep(asyncRouterMap)
        // 不进行权限过滤，直接返回所有路由（后端会验证token）
        const accessedRouters = filterAsyncRouter(routerMap, null)
        commit('SET_ROUTERS', accessedRouters)
        resolve()
      })
    }
  }
}

export default permission
