import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import router from './router'
import PrimeVue from 'primevue/config'

// PrimeVue components
import FileUpload from 'primevue/fileupload'
import ProgressSpinner from 'primevue/progressspinner'
import Message from 'primevue/message'
import Card from 'primevue/card'
import Button from 'primevue/button'
import InputText from 'primevue/inputtext'
import Password from 'primevue/password'
import Dropdown from 'primevue/dropdown'
import InputNumber from 'primevue/inputnumber'
import Dialog from 'primevue/dialog'
import Textarea from 'primevue/textarea'
import Checkbox from 'primevue/checkbox'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import ColumnGroup from 'primevue/columngroup'
import Row from 'primevue/row'
import Tag from 'primevue/tag'
import ConfirmDialog from 'primevue/confirmdialog'
import Toast from 'primevue/toast'
import ToastService from 'primevue/toastservice'
import ConfirmationService from 'primevue/confirmationservice'
import Accordion from 'primevue/accordion'
import AccordionTab from 'primevue/accordiontab'
import Divider from 'primevue/divider'
import ProgressBar from 'primevue/progressbar'
import Paginator from 'primevue/paginator'
import RouterLink from 'primevue/routerlink'
import Tooltip from 'primevue/tooltip'

// PrimeVue styles
import 'primevue/resources/themes/lara-light-blue/theme.css'
import 'primevue/resources/primevue.min.css'
import 'primeicons/primeicons.css'

const app = createApp(App)
const pinia = createPinia()

// Use plugins
app.use(PrimeVue, { ripple: true })
app.use(pinia)
app.use(router)
app.use(ToastService)
app.use(ConfirmationService)
app.use(Tooltip)

// Register PrimeVue components
app.component('FileUpload', FileUpload)
app.component('ProgressSpinner', ProgressSpinner)
app.component('Message', Message)
app.component('Card', Card)
app.component('Button', Button)
app.component('InputText', InputText)
app.component('Password', Password)
app.component('Dropdown', Dropdown)
app.component('InputNumber', InputNumber)
app.component('Dialog', Dialog)
app.component('Textarea', Textarea)
app.component('Checkbox', Checkbox)
app.component('DataTable', DataTable)
app.component('Column', Column)
app.component('ColumnGroup', ColumnGroup)
app.component('Row', Row)
app.component('Tag', Tag)
app.component('ConfirmDialog', ConfirmDialog)
app.component('Toast', Toast)
app.component('Accordion', Accordion)
app.component('AccordionTab', AccordionTab)
app.component('Divider', Divider)
app.component('ProgressBar', ProgressBar)
app.component('Paginator', Paginator)

app.mount('#app')
