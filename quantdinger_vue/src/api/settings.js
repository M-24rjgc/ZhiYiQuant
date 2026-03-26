import request from '@/utils/request'

/**
 * 获取配置项定义
 */
export function getSettingsSchema () {
  return request({
    url: '/api/settings/schema',
    method: 'get'
  })
}

/**
 * 获取当前配置值
 */
export function getSettingsValues () {
  return request({
    url: '/api/settings/values',
    method: 'get'
  })
}

/**
 * 保存配置
 * @param {Object} data - 配置数据
 */
export function saveSettings (data) {
  return request({
    url: '/api/settings/save',
    method: 'post',
    data
  })
}

/**
 * 测试API连接
 * @param {string} service - 服务名称 (openrouter, finnhub, etc.)
 * @param {Object} params - 额外参数
 */
export function testConnection (service, params = {}) {
  return request({
    url: '/api/settings/test-connection',
    method: 'post',
    data: { service, ...params }
  })
}

/**
 * 查询 OpenRouter 账户余额
 */
export function getOpenRouterBalance () {
  return request({
    url: '/api/settings/openrouter-balance',
    method: 'get'
  })
}
