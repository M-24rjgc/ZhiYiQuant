// eslint-disable-next-line
import { UserLayout, BasicLayout } from '@/layouts'

export const asyncRouterMap = [
  {
    path: '/',
    name: 'index',
    component: BasicLayout,
    meta: { title: 'menu.home' },
    redirect: '/dashboard',
    children: [
      {
        path: '/dashboard',
        name: 'Dashboard',
        component: () => import('@/views/dashboard'),
        meta: { title: 'menu.dashboard', keepAlive: true, icon: 'dashboard' }
      },
      {
        path: '/ai-analysis/:pageNo([1-9]\\d*)?',
        name: 'Analysis',
        component: () => import('@/views/ai-analysis'),
        meta: { title: 'menu.dashboard.analysis', keepAlive: false, icon: 'thunderbolt' }
      },
      {
        path: '/indicator-analysis',
        name: 'Indicator',
        component: () => import('@/views/indicator-analysis'),
        meta: { title: 'menu.dashboard.indicator', keepAlive: true, icon: 'line-chart' }
      },
      {
        path: '/trading-assistant',
        name: 'TradingAssistant',
        component: () => import('@/views/trading-assistant'),
        meta: { title: 'menu.dashboard.tradingAssistant', keepAlive: true, icon: 'robot' }
      },
      {
        path: '/portfolio',
        name: 'Portfolio',
        component: () => import('@/views/portfolio'),
        meta: { title: 'menu.dashboard.portfolio', keepAlive: true, icon: 'fund' }
      },
      {
        path: '/profile',
        name: 'Profile',
        component: () => import('@/views/profile'),
        meta: { title: 'menu.myProfile', keepAlive: false, icon: 'user' }
      },
      {
        path: '/settings',
        name: 'Settings',
        component: () => import('@/views/settings'),
        meta: { title: 'menu.settings', keepAlive: false, icon: 'setting' }
      }
    ]
  },
  {
    path: '*',
    redirect: '/404',
    hidden: true
  }
]

export const constantRouterMap = [
  {
    path: '/user',
    component: UserLayout,
    redirect: '/user/login',
    hidden: true,
    children: [
      {
        path: 'login',
        name: 'login',
        component: () => import(/* webpackChunkName: "user" */ '@/views/user/Login')
      }
    ]
  },
  {
    path: '/404',
    component: () => import(/* webpackChunkName: "fail" */ '@/views/exception/404')
  }
]
