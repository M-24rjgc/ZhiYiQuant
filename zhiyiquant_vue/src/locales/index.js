import Vue from 'vue'
import VueI18n from 'vue-i18n'
import storage from 'store'
import moment from 'moment'

import enUS from './lang/en-US'
import zhCN from './lang/zh-CN'

Vue.use(VueI18n)

export const defaultLang = 'zh-CN'

const messages = {
  'en-US': {
    ...enUS
  },
  'zh-CN': {
    ...zhCN
  }
}

const i18n = new VueI18n({
  silentTranslationWarn: true,
  locale: defaultLang,
  fallbackLocale: defaultLang,
  messages
})

const loadedLanguages = Object.keys(messages)

function setI18nLanguage (lang) {
  i18n.locale = lang
  const locale = messages[lang] || {}
  if (locale.momentName) {
    if (locale.momentLocale && Object.keys(locale.momentLocale).length) {
      moment.updateLocale(locale.momentName, locale.momentLocale)
    }
    moment.locale(locale.momentName)
  }
  const html = document.documentElement
  const isRtl = /^ar/i.test(lang)

  if (html) {
    html.setAttribute('lang', lang)
    html.setAttribute('dir', isRtl ? 'rtl' : 'ltr')
  }

  if (document.body) {
    document.body.setAttribute('dir', isRtl ? 'rtl' : 'ltr')
    document.body.classList.toggle('rtl', isRtl)
  }

  return lang
}

export function loadLanguageAsync (lang = defaultLang) {
  const targetLang = messages[lang] ? lang : defaultLang
  storage.set('lang', targetLang)

  if (i18n.locale === targetLang) {
    return Promise.resolve(setI18nLanguage(targetLang))
  }

  if (loadedLanguages.includes(targetLang)) {
    return Promise.resolve(setI18nLanguage(targetLang))
  }

  return import(/* webpackChunkName: "lang-[request]" */ `./lang/${targetLang}`).then(msg => {
    const locale = msg.default
    i18n.setLocaleMessage(targetLang, locale)
    loadedLanguages.push(targetLang)
    moment.updateLocale(locale.momentName, locale.momentLocale)
    return setI18nLanguage(targetLang)
  })
}

export function i18nRender (key) {
  return i18n.t(`${key}`)
}

export default i18n
