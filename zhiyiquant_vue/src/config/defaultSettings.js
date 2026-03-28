export const PYTHON_API_BASE_URL = process.env.VUE_APP_PYTHON_API_BASE_URL || 'http://localhost:5000'

export default {
  navTheme: 'light',
  primaryColor: '#13C2C2',
  layout: 'sidemenu',
  contentWidth: 'Fluid',
  fixedHeader: true,
  fixSiderbar: true,
  colorWeak: false,
  menu: {
    locale: true
  },
  title: '智弈量化',
  pwa: false,
  iconfontUrl: '',
  production: process.env.NODE_ENV === 'production' && process.env.VUE_APP_PREVIEW !== 'true'
}
