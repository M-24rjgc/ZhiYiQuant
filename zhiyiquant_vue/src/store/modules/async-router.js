import { constantRouterMap, asyncRouterMap } from '@/config/router.config'

const permission = {
  state: {
    routers: constantRouterMap,
    addRouters: [],
    isDynamicRoutesReady: false
  },
  mutations: {
    SET_ROUTERS: (state, routers) => {
      state.addRouters = routers
      state.routers = constantRouterMap.concat(routers)
      state.isDynamicRoutesReady = true
    },
    RESET_ROUTERS: (state) => {
      state.addRouters = []
      state.routers = constantRouterMap
      state.isDynamicRoutesReady = false
    }
  },
  actions: {
    GenerateRoutes ({ commit }) {
      commit('SET_ROUTERS', asyncRouterMap)
      return Promise.resolve(asyncRouterMap)
    },
    ResetRoutes ({ commit }) {
      commit('RESET_ROUTERS')
    }
  }
}

export default permission
