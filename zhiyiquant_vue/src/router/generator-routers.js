import { asyncRouterMap } from '@/config/router.config'

export const generatorDynamicRouter = () => {
  return Promise.resolve(asyncRouterMap)
}
