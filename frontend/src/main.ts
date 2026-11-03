import { createApp } from 'vue'
import { createVuetify } from 'vuetify'
import { VAlert, VApp, VAutocomplete, VBtn, VCard, VChip, VIcon, VSelect } from 'vuetify/components'
import { Ripple } from 'vuetify/directives'
import { mdi } from 'vuetify/iconsets/mdi'
import 'vuetify/styles'
import '@mdi/font/css/materialdesignicons.css'
import App from './App.vue'
import './style.css'
import './new-features.css'
import './catalog.css'
import './foodcom.css'
import './home-foodcom.css'
import './recipe-picker.css'
import './research.css'
import './portal.css'
import './kg.css'
import './kg-explore.css'
import './link-prediction.css'
import './diy-confidence.css'
import './material-theme.css'
import './login.css'

const vuetify = createVuetify({
  components: { VAlert, VApp, VAutocomplete, VBtn, VCard, VChip, VIcon, VSelect },
  directives: { Ripple },
  icons: { defaultSet: 'mdi', sets: { mdi } },
  theme: {
    defaultTheme: 'nutri',
    themes: {
      nutri: {
        dark: false,
        colors: {
          primary: '#1688C0',
          secondary: '#587B91',
          surface: '#FFFFFF',
          background: '#F3F8FB',
          error: '#B74139',
          info: '#2AA9C6',
        },
      },
    },
  },
  defaults: {
    VBtn: { rounded: 'lg', elevation: 0, style: 'text-transform: none' },
    VTextField: { variant: 'outlined', density: 'comfortable', hideDetails: 'auto' },
    VSelect: { variant: 'outlined', density: 'comfortable', hideDetails: 'auto' },
    VTextarea: { variant: 'outlined', density: 'comfortable', hideDetails: 'auto' },
  },
})

createApp(App).use(vuetify).mount('#app')

