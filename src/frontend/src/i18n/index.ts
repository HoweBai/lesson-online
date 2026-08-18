import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';
import LanguageDetector from 'i18next-browser-languagedetector';

import commonEn from './locales/en/common.json';
import commonZh from './locales/zh/common.json';
import authEn from './locales/en/auth.json';
import authZh from './locales/zh/auth.json';
import tutorialsEn from './locales/en/tutorials.json';
import tutorialsZh from './locales/zh/tutorials.json';
import adminEn from './locales/en/admin.json';
import adminZh from './locales/zh/admin.json';
import wizardEn from './locales/en/wizard.json';
import wizardZh from './locales/zh/wizard.json';
import shareEn from './locales/en/share.json';
import shareZh from './locales/zh/share.json';
import chatEn from './locales/en/chat.json';
import chatZh from './locales/zh/chat.json';

i18n
  .use(LanguageDetector)
  .use(initReactI18next)
  .init({
    resources: {
      en: {
        common: commonEn,
        auth: authEn,
        tutorials: tutorialsEn,
        admin: adminEn,
        wizard: wizardEn,
        share: shareEn,
        chat: chatEn,
      },
      zh: {
        common: commonZh,
        auth: authZh,
        tutorials: tutorialsZh,
        admin: adminZh,
        wizard: wizardZh,
        share: shareZh,
        chat: chatZh,
      },
    },
    fallbackLng: 'en',
    supportedLngs: ['en', 'zh'],
    interpolation: {
      escapeValue: false,
    },
    ns: ['common', 'auth', 'tutorials', 'admin', 'wizard', 'share', 'chat'],
    defaultNS: 'common',
  });

export default i18n;
