
import request from '@/utils/request'

// Dashboard API
const api = {
  summary: '/api/dashboard/summary',
  pendingOrders: '/api/dashboard/pendingOrders'
}

export function getDashboardSummary () {
  return request({
    url: api.summary,
    method: 'get'
  })
}

export function getPendingOrders (params) {
  return request({
    url: api.pendingOrders,
    method: 'get',
    params
  })
}

export function deletePendingOrder (id) {
  return request({
    url: `${api.pendingOrders}/${id}`,
    method: 'delete'
  })
}
