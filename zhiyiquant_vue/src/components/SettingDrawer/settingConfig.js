import message from 'ant-design-vue/es/message'
// import defaultSettings from '../defaultSettings';
import themeColor from './themeColor.js'
import i18n from '@/locales'

// let lessNodesAppended
const getColorList = () => {
  return [
    {
      key: i18n.t('app.setting.themecolor.dust'), color: '#F5222D'
    },
    {
      key: i18n.t('app.setting.themecolor.volcano'), color: '#FA541C'
    },
    {
      key: i18n.t('app.setting.themecolor.sunset'), color: '#FAAD14'
    },
    {
      key: i18n.t('app.setting.themecolor.cyan'), color: '#13C2C2'
    },
    {
      key: i18n.t('app.setting.themecolor.green'), color: '#52C41A'
    },
    {
      key: i18n.t('app.setting.themecolor.daybreak'), color: '#1890FF'
    },
    {
      key: i18n.t('app.setting.themecolor.geekblue'), color: '#2F54EB'
    },
    {
      key: i18n.t('app.setting.themecolor.purple'), color: '#722ED1'
    }
  ]
}

const updateTheme = (newPrimaryColor, silent = false) => {
  const hideMessage = silent ? null : message.loading(i18n.t('app.setting.theme.switching'), 0)
  themeColor.changeColor(newPrimaryColor).finally(() => {
    if (hideMessage) {
      setTimeout(() => {
        hideMessage()
      }, 10)
    }
  })
}

const updateColorWeak = colorWeak => {
  // document.body.className = colorWeak ? 'colorWeak' : '';
  const app = document.body.querySelector('#app')
  colorWeak ? app.classList.add('colorWeak') : app.classList.remove('colorWeak')
}

export { updateTheme, getColorList, updateColorWeak }
