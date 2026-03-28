import Vue from 'vue'
import VueI18n from 'vue-i18n'
import storage from 'store'

import enUS from './lang/en-US'

Vue.use(VueI18n)

export const defaultLang = 'en-US'

const i18n = new VueI18n({
  silentTranslationWarn: true,
  locale: defaultLang,
  fallbackLocale: defaultLang,
  messages: {
    'en-US': {
      ...enUS
    }
  }
})

export function loadLanguageAsync () {
  storage.set('lang', defaultLang)
  const html = document.documentElement
  if (html) {
    html.setAttribute('lang', defaultLang)
    html.setAttribute('dir', 'ltr')
  }
  if (document.body) {
    document.body.setAttribute('dir', 'ltr')
    document.body.classList.remove('rtl')
  }
  return Promise.resolve(defaultLang)
}

export function i18nRender (key) {
  return i18n.t(`${key}`)
}

export default i18n
