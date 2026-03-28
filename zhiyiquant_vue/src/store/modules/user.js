import storage from 'store'
import expirePlugin from 'store/plugins/expire'
import { login, logout, getUserInfo } from '@/api/login'
import { ACCESS_TOKEN, USER_INFO, USER_ROLES } from '@/store/mutation-types'
import { welcome } from '@/utils/util'

storage.addPlugin(expirePlugin)

const DESKTOP_ROLE = [{ id: 'desktop', permissionList: ['desktop'] }]

function getStoredInfo () {
  const info = storage.get(USER_INFO) || {}
  return (info && typeof info === 'object') ? info : {}
}

function getStoredToken () {
  const token = storage.get(ACCESS_TOKEN)
  if (typeof token === 'string') return token
  return token && token.token ? token.token : ''
}

const initialInfo = getStoredInfo()
const initialName = initialInfo.nickname || initialInfo.username || ''

const user = {
  state: {
    token: getStoredToken(),
    name: initialName,
    welcome: initialName ? welcome() : '',
    avatar: initialInfo.avatar || '',
    roles: DESKTOP_ROLE,
    info: initialInfo
  },

  mutations: {
    SET_TOKEN: (state, token) => {
      state.token = token
    },
    SET_NAME: (state, { name, welcome }) => {
      state.name = name
      state.welcome = welcome
    },
    SET_AVATAR: (state, avatar) => {
      state.avatar = avatar
    },
    SET_ROLES: (state, roles) => {
      state.roles = roles
    },
    SET_INFO: (state, info) => {
      state.info = info
    }
  },

  actions: {
    Login ({ commit, dispatch }, userInfo) {
      return new Promise((resolve, reject) => {
        login(userInfo).then(response => {
          if (response && response.code === 1 && response.data) {
            const token = response.data.token
            const info = response.data.userinfo || {}
            const expiresAt = new Date().getTime() + 7 * 24 * 60 * 60 * 1000

            storage.set(ACCESS_TOKEN, token, expiresAt)
            storage.set(USER_INFO, info, expiresAt)
            storage.set(USER_ROLES, DESKTOP_ROLE, expiresAt)

            commit('SET_TOKEN', token)
            commit('SET_INFO', info)
            commit('SET_NAME', { name: info.nickname || info.username || 'Owner', welcome: welcome() })
            commit('SET_AVATAR', info.avatar || '/avatar2.jpg')
            commit('SET_ROLES', DESKTOP_ROLE)

            dispatch('ResetRoutes')
            resolve(response)
          } else {
            reject(new Error((response && response.msg) || 'Login failed'))
          }
        }).catch(reject)
      })
    },

    FetchUserInfo ({ commit }) {
      return new Promise((resolve, reject) => {
        getUserInfo().then(res => {
          if (res && res.code === 1 && res.data) {
            const info = res.data
            commit('SET_INFO', info)
            commit('SET_NAME', { name: info.nickname || info.username || 'Owner', welcome: welcome() })
            commit('SET_AVATAR', info.avatar || '/avatar2.jpg')
            commit('SET_ROLES', DESKTOP_ROLE)
            storage.set(USER_INFO, info, new Date().getTime() + 7 * 24 * 60 * 60 * 1000)
            storage.set(USER_ROLES, DESKTOP_ROLE, new Date().getTime() + 7 * 24 * 60 * 60 * 1000)
            resolve(info)
          } else {
            reject(new Error((res && res.msg) || 'Failed to load user info'))
          }
        }).catch(reject)
      })
    },

    GetInfo ({ dispatch, state }) {
      if (state.info && state.info.username) {
        return Promise.resolve(state.info)
      }
      return dispatch('FetchUserInfo')
    },

    Logout ({ commit, dispatch }) {
      return new Promise((resolve) => {
        logout().catch(() => {}).finally(() => {
          commit('SET_TOKEN', '')
          commit('SET_ROLES', DESKTOP_ROLE)
          commit('SET_INFO', {})
          commit('SET_NAME', { name: '', welcome: '' })
          commit('SET_AVATAR', '')
          storage.remove(ACCESS_TOKEN)
          storage.remove(USER_INFO)
          storage.remove(USER_ROLES)
          dispatch('ResetRoutes')
          resolve()
        })
      })
    }
  }
}

export default user
