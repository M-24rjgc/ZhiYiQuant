import request from '@/utils/request'

const userApi = {
  Login: '/api/auth/login',
  Logout: '/api/auth/logout',
  UserInfo: '/api/auth/info'
}

export function login (parameter) {
  return request({
    url: userApi.Login,
    method: 'post',
    data: parameter
  })
}

export function getInfo () {
  return request({
    url: userApi.UserInfo,
    method: 'get',
    headers: {
      'Content-Type': 'application/json;charset=UTF-8'
    }
  })
}

export function getUserInfo () {
  return getInfo()
}

export function logout () {
  return request({
    url: userApi.Logout,
    method: 'post',
    headers: {
      'Content-Type': 'application/json;charset=UTF-8'
    }
  })
}
