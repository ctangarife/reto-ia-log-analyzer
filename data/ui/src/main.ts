import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import PrimeVue from 'primevue/config'

// PrimeVue components
import FileUpload from 'primevue/fileupload'
import ProgressSpinner from 'primevue/progressspinner'
import Message from 'primevue/message'
import Card from 'primevue/card'
import Button from 'primevue/button'

// PrimeVue styles
import 'primevue/resources/themes/lara-light-blue/theme.css'
import 'primevue/resources/primevue.min.css'
import 'primeicons/primeicons.css'

const app = createApp(App)
const pinia = createPinia()

// Use plugins
app.use(PrimeVue)
app.use(pinia)

// Register PrimeVue components
app.component('FileUpload', FileUpload)
app.component('ProgressSpinner', ProgressSpinner)
app.component('Message', Message)
app.component('Card', Card)
app.component('Button', Button)

app.mount('#app')
