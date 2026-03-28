import request from '@/utils/request'

const marketApi = {
  getWatchlist: '/api/market/watchlist/get',
  addWatchlist: '/api/market/watchlist/add',
  addWatchlistBatch: '/api/market/watchlist/batch-add',
  removeWatchlist: '/api/market/watchlist/remove',
  getWatchlistPrices: '/api/market/watchlist/prices',
  chatMessage: '/api/ai/chat/message',
  getChatHistory: '/api/ai/chat/history',
  saveChatHistory: '/api/ai/chat/history/save',
  getConfig: '/api/market/config',
  getMenuFooterConfig: '/api/market/menuFooterConfig',
  getMarketTypes: '/api/market/types',
  searchSymbols: '/api/market/symbols/search',
  getHotSymbols: '/api/market/symbols/hot'
}

export function getWatchlist (params = {}) {
  return request({
    url: marketApi.getWatchlist,
    method: 'get',
    params
  })
}

export function addWatchlist (data) {
  return request({
    url: marketApi.addWatchlist,
    method: 'post',
    data
  })
}

export function addWatchlistBatch (data) {
  return request({
    url: marketApi.addWatchlistBatch,
    method: 'post',
    data
  })
}

export function removeWatchlist (data) {
  return request({
    url: marketApi.removeWatchlist,
    method: 'post',
    data
  })
}

export function getWatchlistPrices ({ watchlist = [] } = {}) {
  return request({
    url: marketApi.getWatchlistPrices,
    method: 'get',
    params: {
      watchlist: JSON.stringify(watchlist)
    }
  })
}

export function chatMessage (data) {
  return request({
    url: marketApi.chatMessage,
    method: 'post',
    data
  })
}

export function getChatHistory (params = {}) {
  return request({
    url: marketApi.getChatHistory,
    method: 'get',
    params
  })
}

export function saveChatHistory (data) {
  return request({
    url: marketApi.saveChatHistory,
    method: 'post',
    data
  })
}

export function getConfig () {
  return request({
    url: marketApi.getConfig,
    method: 'get'
  })
}

export function getMenuFooterConfig () {
  return request({
    url: marketApi.getMenuFooterConfig,
    method: 'get'
  })
}

export function getMarketTypes () {
  return request({
    url: marketApi.getMarketTypes,
    method: 'get'
  })
}

export function searchSymbols (params = {}) {
  return request({
    url: marketApi.searchSymbols,
    method: 'get',
    params
  })
}

export function getHotSymbols (params = {}) {
  return request({
    url: marketApi.getHotSymbols,
    method: 'get',
    params
  })
}
