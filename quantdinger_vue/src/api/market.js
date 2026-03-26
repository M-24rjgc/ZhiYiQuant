import request, { ANALYSIS_TIMEOUT } from '@/utils/request'

const marketApi = {
  // Watchlist
  GetWatchlist: '/api/market/watchlist/get',
  AddWatchlist: '/api/market/watchlist/add',
  AddWatchlistBatch: '/api/market/watchlist/batch-add',
  RemoveWatchlist: '/api/market/watchlist/remove',
  GetWatchlistPrices: '/api/market/watchlist/prices',
  // Analysis
  MultiAnalysis: '/api/analysis/multiAnalysis',
  CreateAnalysisTask: '/api/analysis/createTask',
  GetAnalysisTaskStatus: '/api/analysis/getTaskStatus',
  GetAnalysisHistoryList: '/api/analysis/getHistoryList',
  DeleteAnalysisTask: '/api/analysis/deleteTask',
  ReflectAnalysis: '/api/analysis/reflect',
  // AI chat (optional)
  ChatMessage: '/api/ai/chat/message',
  GetChatHistory: '/api/ai/chat/history',
  SaveChatHistory: '/api/ai/chat/history/save',
  // Public config
  GetConfig: '/api/market/config',
  GetMenuFooterConfig: '/api/market/menuFooterConfig',
  // Market metadata
  GetMarketTypes: '/api/market/types',
  // Symbol search
  SearchSymbols: '/api/market/symbols/search',
  GetHotSymbols: '/api/market/symbols/hot'
}

/**
 * 获取自选股列表
 * @param parameter { userid: number }
 * @returns {*}
 */
export function getWatchlist (parameter) {
  return request({
    url: marketApi.GetWatchlist,
    method: 'get',
    params: parameter
  })
}

/**
 * 添加自选股
 * @param parameter { userid: number, market: string, symbol: string }
 * @returns {*}
 */
export function addWatchlist (parameter) {
  return request({
    url: marketApi.AddWatchlist,
    method: 'post',
    data: parameter
  })
}

/**
 * 批量添加自选股
 * @param parameter { items: [{market: string, symbol: string, name?: string}] }
 * @returns {*}
 */
export function addWatchlistBatch (parameter) {
  return request({
    url: marketApi.AddWatchlistBatch,
    method: 'post',
    data: parameter
  })
}

/**
 * 删除自选股
 * @param parameter { userid: number, symbol: string }
 * @returns {*}
 */
export function removeWatchlist (parameter) {
  return request({
    url: marketApi.RemoveWatchlist,
    method: 'post',
    data: parameter
  })
}

/**
 * 获取自选股价格
 * @param parameter { watchlist: array } watchlist格式：[{market: 'USStock', symbol: 'AAPL'}, ...]
 * @returns {*}
 */
export function getWatchlistPrices (parameter) {
  return request({
    url: marketApi.GetWatchlistPrices,
    method: 'get',
    params: {
      watchlist: JSON.stringify(parameter.watchlist || [])
    }
  })
}

/**
 * 发送 AI 聊天消息
 * @param parameter { userid: number, message: string, chatId?: string }
 * @returns {*}
 */
export function chatMessage (parameter) {
  return request({
    url: marketApi.ChatMessage,
    method: 'post',
    data: parameter
  })
}

/**
 * 获取聊天历史
 * @param parameter { userid: number }
 * @returns {*}
 */
export function getChatHistory (parameter) {
  return request({
    url: marketApi.GetChatHistory,
    method: 'get',
    params: parameter
  })
}

/**
 * 保存聊天历史
 * @param parameter { userid: number, chatHistory: array }
 * @returns {*}
 */
export function saveChatHistory (parameter) {
  return request({
    url: marketApi.SaveChatHistory,
    method: 'post',
    data: parameter
  })
}

/**
 * 执行多维度分析
 * @param parameter { userid: number, market: string, symbol: string }
 * @returns {*}
 */
export function multiAnalysis (parameter) {
  return request({
    url: marketApi.MultiAnalysis,
    method: 'post',
    data: parameter,
    timeout: ANALYSIS_TIMEOUT // Extended timeout for AI analysis
  })
}

/**
 * 创建分析任务
 * @param parameter { userid: number, market: string, symbol: string }
 * @returns {*}
 */
export function createAnalysisTask (parameter) {
  return request({
    url: marketApi.CreateAnalysisTask,
    method: 'post',
    data: parameter
  })
}

/**
 * 获取分析任务状态
 * @param parameter { task_id: number }
 * @returns {*}
 */
export function getAnalysisTaskStatus (parameter) {
  return request({
    url: marketApi.GetAnalysisTaskStatus,
    method: 'get',
    params: parameter
  })
}

/**
 * 获取历史分析列表
 * @param parameter { userid: number, page?: number, pagesize?: number }
 * @returns {*}
 */
export function getAnalysisHistoryList (parameter) {
  return request({
    url: marketApi.GetAnalysisHistoryList,
    method: 'get',
    params: parameter
  })
}

/**
 * Delete analysis task
 * @param parameter { task_id: number }
 * @returns {*}
 */
export function deleteAnalysisTask (parameter) {
  return request({
    url: marketApi.DeleteAnalysisTask,
    method: 'post',
    data: parameter
  })
}

/**
 * 反思学习
 * @param parameter { market: string, symbol: string, decision: string, returns?: number, result?: string }
 * @returns {*}
 */
export function reflectAnalysis (parameter) {
  return request({
    url: marketApi.ReflectAnalysis,
    method: 'post',
    data: parameter
  })
}

/**
 * 获取插件配置
 * @returns {*}
 */
export function getConfig () {
  return request({
    url: marketApi.GetConfig,
    method: 'get'
  })
}

/**
 * 获取菜单底部配置
 * @returns {*}
 */
export function getMenuFooterConfig () {
  return request({
    url: marketApi.GetMenuFooterConfig,
    method: 'get'
  })
}

/**
 * 获取股票类型列表
 * @returns {*}
 */
export function getMarketTypes () {
  return request({
    url: marketApi.GetMarketTypes,
    method: 'get'
  })
}

/**
 * 搜索金融产品
 * @param parameter { market: string, keyword: string, limit?: number }
 * @returns {*}
 */
export function searchSymbols (parameter) {
  return request({
    url: marketApi.SearchSymbols,
    method: 'get',
    params: parameter
  })
}

/**
 * 获取热门标的
 * @param parameter { market: string, limit?: number }
 * @returns {*}
 */
export function getHotSymbols (parameter) {
  return request({
    url: marketApi.GetHotSymbols,
    method: 'get',
    params: parameter
  })
}
