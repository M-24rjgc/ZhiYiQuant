import request from '@/utils/request'

export function getProfile () {
  return request({
    url: '/api/users/profile',
    method: 'get'
  })
}

export function updateProfile (data) {
  return request({
    url: '/api/users/profile/update',
    method: 'put',
    data
  })
}

export function changePassword (data) {
  return request({
    url: '/api/users/change-password',
    method: 'post',
    data
  })
}

export function getNotificationSettings () {
  return request({
    url: '/api/users/notification-settings',
    method: 'get'
  })
}

export function updateNotificationSettings (data) {
  return request({
    url: '/api/users/notification-settings',
    method: 'put',
    data
  })
}

export function testNotification () {
  return request({
    url: '/api/users/test-notification',
    method: 'post'
  })
}
