import { createRouter, createWebHistory, RouteRecordRaw } from 'vue-router'
import { useAuthStore } from '../stores/authStore'
import AppLayout from '../components/AppLayout.vue'

// Lazy load components
const Login = () => import('../components/Login.vue')
const Register = () => import('../components/Register.vue')
const AnalysisView = () => import('../views/AnalysisView.vue')
const AnalysisDetailView = () => import('../views/AnalysisDetailView.vue')
const HistoryView = () => import('../views/HistoryView.vue')
const LearningView = () => import('../views/LearningView.vue')
const AdminView = () => import('../views/AdminView.vue')
const LLMModelSelection = () => import('../components/LLMModelSelection.vue')

const routes: RouteRecordRaw[] = [
  // Rutas públicas (SIN AppLayout)
  {
    path: '/login',
    name: 'login',
    component: Login,
    meta: { public: true }
  },
  {
    path: '/register',
    name: 'register',
    component: Register,
    meta: { public: true }
  },

  // Rutas protegidas (CON AppLayout)
  {
    path: '/',
    component: AppLayout,
    children: [
      {
        path: '',
        redirect: '/analysis'
      },
      {
        path: 'analysis',
        name: 'analysis',
        component: AnalysisView
      },
      {
        path: 'analysis/:id',
        name: 'analysis-detail',
        component: AnalysisDetailView,
        props: true
      },
      {
        path: 'history',
        name: 'history',
        component: HistoryView
      },
      {
        path: 'history/:id',
        name: 'history-detail',
        redirect: to => ({ name: 'analysis-detail', params: { id: to.params.id } })
      },
      {
        path: 'learning',
        name: 'learning',
        component: LearningView
      },
      {
        path: 'llm-models',
        name: 'llm-models',
        component: LLMModelSelection
      },
      {
        path: 'admin',
        name: 'admin',
        component: AdminView,
        meta: { requiresSuperAdmin: true }
      }
    ]
  },

  // Catch-all - redirige según autenticación
  {
    path: '/:pathMatch(.*)*',
    redirect: to => {
      const authStore = useAuthStore()
      return authStore.isLoggedIn ? '/analysis' : '/login'
    }
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

// Navigation guard - verifica permisos correctamente
router.beforeEach(async (to, from, next) => {
  const authStore = useAuthStore()

  // 1. Esperar a que el store esté inicializado
  if (!authStore.isInitialized) {
    // App.vue está mostrando loading, dejar pasar
    next()
    return
  }

  // 2. Una vez inicializado, verificar permisos
  const isPublicRoute = to.meta.public === true

  // Rutas públicas (login, register)
  if (isPublicRoute) {
    if (authStore.isLoggedIn && (to.name === 'login' || to.name === 'register')) {
      // Usuario ya logueado intentando acceder a login/register
      next({ name: 'analysis' })
    } else {
      next()
    }
    return
  }

  // 3. Rutas protegidas - verificar autenticación
  if (!authStore.isLoggedIn) {
    // No está logueado, redirigir a login
    next({ name: 'login', query: { redirect: to.fullPath } })
    return
  }

  // 4. Verificar super admin si es requerido
  if (to.meta.requiresSuperAdmin && !authStore.isSuperAdmin) {
    next({ name: 'analysis' })
    return
  }

  // 5. Todo está correcto, permitir paso
  next()
})

export default router
