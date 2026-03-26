import { isIE } from '@/utils/util'

// 本地开发已有完整后端 API，禁用 mock 以避免请求被拦截
// 如需启用 mock，将下面的 false 改为 true
const ENABLE_MOCK = false

// 判断环境不是 prod 或者 preview 是 true 时，加载 mock 服务
if (ENABLE_MOCK && (process.env.NODE_ENV !== 'production' || process.env.VUE_APP_PREVIEW === 'true')) {
  if (isIE()) {
  }
  // 使用同步加载依赖
  // 防止 vuex 中的 GetInfo 早于 mock 运行，导致无法 mock 请求返回结果
  const Mock = require('mockjs2')
  require('./services/auth')
  require('./services/user')
  require('./services/manage')
  require('./services/other')
  require('./services/tagCloud')
  require('./services/article')

  Mock.setup({
    timeout: 800 // setter delay time
  })
}
