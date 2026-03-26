import Vue from 'vue'
import Vuex from 'vuex'

import app from './modules/app'
import user from './modules/user'

// dynamic router permission control
// 动态路由模式（支持基于角色的菜单过滤）
import permission from './modules/async-router'

// static router permission control (NO filtering)
// 静态路由模式（不过滤菜单，已弃用）
// import permission from './modules/static-router'

import getters from './getters'

Vue.use(Vuex)

export default new Vuex.Store({
  modules: {
    app,
    user,
    permission
  },
  state: {},
  mutations: {},
  actions: {},
  getters
})
