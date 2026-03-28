import { constantRouterMap, asyncRouterMap } from '@/config/router.config'

const permission = {
  state: {
    routers: constantRouterMap,
    addRouters: []
  },
  mutations: {
    SET_ROUTERS: (state, routers) => {
      state.addRouters = routers
      state.routers = constantRouterMap.concat(routers)
    },
    RESET_ROUTERS: (state) => {
      state.addRouters = []
      state.routers = constantRouterMap
    }
  },
  actions: {
    GenerateRoutes ({ commit }) {
      commit('SET_ROUTERS', asyncRouterMap)
      return Promise.resolve()
    },
    ResetRoutes ({ commit }) {
      commit('RESET_ROUTERS')
    }
  }
}

export default permission
