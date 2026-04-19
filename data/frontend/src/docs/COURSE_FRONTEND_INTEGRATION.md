# Integración del Sistema de Cursos - Frontend

## Resumen de Archivos Creados

### Servicios TypeScript
- `services/courseGenerationService.ts` - API calls para generación de cursos
- `services/courseRBACService.ts` - Gestión de roles y permisos
- `services/lessonEditService.ts` - Edición granular de lecciones
- `services/courseProgressService.ts` - Progreso del curso (usuarios)

### Componentes Vue
- `components/CourseGenerateDialog.vue` - Diálogo para generar cursos
- `components/CourseReviewPanel.vue` - Panel de revisión de cursos pendientes
- `components/CourseViewer.vue` - Visualizador de curso para estudiantes
- `components/CourseRoleManager.vue` - Gestor de roles de curso
- `components/CourseManagementWidget.vue` - Widget integrador principal

### Store
- `stores/courseStore.ts` - Estado global de cursos

## Integración en App.vue

```vue
<template>
  <div id="app">
    <!-- Navigation -->
    <Menubar class="mb-3">
      <template #end>
        <Button v-if="currentUser" label="Mis Cursos" @click="showMyCourses" />
        <Button v-if="hasCourseAdmin" label="Administrar Cursos" @click="showCourseAdmin" />
      </template>
    </Menubar>

    <!-- Main Content -->
    <router-view />

    <!-- Course Management Widget -->
    <CourseManagementWidget
      v-if="currentProject && hasCoursePermissions"
      :projectId="currentProject.id"
      :workspaceId="currentWorkspace.id"
      :workspaceUsers="workspaceUsers"
      ref="courseWidget"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useCourseStore } from '@/stores/courseStore'
import { courseRBACService } from '@/services/courseRBACService'
import CourseManagementWidget from '@/components/CourseManagementWidget.vue'

const currentProject = ref(null)
const currentWorkspace = ref(null)
const currentUser = ref(null)
const workspaceUsers = ref([])
const courseWidget = ref()

const courseStore = useCourseStore()

const hasCoursePermissions = computed(() => {
  return courseStore.canGenerateCourse ||
         courseStore.canReviewCourses ||
         courseStore.canEditCourses
})

const hasCourseAdmin = computed(() => {
  return courseStore.isCourseAdmin
})

onMounted(async () => {
  // Load current workspace and project
  await loadWorkspaceData()

  // Load user's course permissions
  if (currentWorkspace.value) {
    await loadPermissions()
  }
})

const loadWorkspaceData = async () => {
  // Load from your existing stores/route params
  // ...
}

const loadPermissions = async () => {
  try {
    const perms = await courseRBACService.getMyPermissions(currentWorkspace.value.id)
    courseStore.setPermissions(perms.permissions)
    courseStore.setRoles(perms.roles.map(r => r.name))
  } catch (e) {
    console.error('Failed to load permissions:', e)
  }
}

const showMyCourses = () => {
  // Navigate to courses view or show course viewer
  router.push('/courses')
}

const showCourseAdmin = () => {
  // Open course management interface
  courseWidget.value?.openRoleManager()
}
</script>
```

## Vista de Cursos (Nueva Página)

```vue
<!-- pages/CoursesPage.vue -->
<template>
  <div class="courses-page">
    <div class="flex justify-content-between align-items-center mb-4">
      <h1>Mis Cursos</h1>
      <Button
        v-if="canGenerateCourse"
        icon="pi pi-plus"
        label="Crear Curso"
        @click="openGenerateDialog"
      />
    </div>

    <!-- Tabs -->
    <TabView>
      <!-- Available Courses -->
      <TabPanel header="Cursos Disponibles">
        <CourseViewer
          v-for="course in publishedCourses"
          :key="course.id"
          :projectId="course.project_id"
        />
      </TabPanel>

      <!-- In Progress -->
      <TabPanel header="En Progreso">
        <CourseViewer
          v-for="course in inProgressCourses"
          :key="course.id"
          :projectId="course.project_id"
        />
      </TabPanel>

      <!-- Completed -->
      <TabPanel header="Completados">
        <CourseViewer
          v-for="course in completedCourses"
          :key="course.id"
          :projectId="course.project_id"
        />
      </TabPanel>
    </TabView>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useCourseStore } from '@/stores/courseStore'

const courseStore = useCourseStore()

const allCourses = computed(() => courseStore.courses)

const publishedCourses = computed(() =>
  allCourses.value.filter(c => c.status === 'published')
)

const inProgressCourses = computed(() =>
  allCourses.value.filter(c => c.progress_percentage > 0 && c.progress_percentage < 100)
)

const completedCourses = computed(() =>
  allCourses.value.filter(c => c.is_completed)
)

const canGenerateCourse = computed(() => courseStore.canGenerateCourse)
</script>
```

## Ejemplo en Proyecto Existente

Para agregar el widget de gestión de cursos a una vista de proyecto existente:

```vue
<!-- En tu vista de proyecto (ProjectView.vue o similar) -->
<template>
  <div class="project-view">
    <!-- Existing project content -->

    <!-- Add Course Management -->
    <div v-if="project" class="mt-4">
      <Panel header="Curso del Proyecto">
        <template #content>
          <!-- No course yet -->
          <div v-if="!hasCourse" class="text-center p-4">
            <p class="text-color-secondary mb-3">
              Este proyecto aún no tiene un curso interactivo.
            </p>
            <Button
              v-if="canGenerateCourse"
              label="Generar Curso"
              icon="pi pi-plus"
              @click="generateCourse"
            />
          </div>

          <!-- Course exists -->
          <CourseViewer
            v-else
            :projectId="project.id"
          />
        </template>
      </Panel>
    </div>

    <!-- Hidden Widget for Management -->
    <CourseManagementWidget
      v-if="project"
      ref="courseWidget"
      :projectId="project.id"
      :workspaceId="project.workspace_id"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useCourseStore } from '@/stores/courseStore'

const props = defineProps<{
  project: {
    type: Object,
    required: true
  }
}>()

const courseStore = useCourseStore()
const courseWidget = ref()

const canGenerateCourse = computed(() => courseStore.canGenerateCourse)
const hasCourse = computed(() => {
  return courseStore.courses.some(c => c.project_id === props.project.id)
})

const generateCourse = () => {
  courseWidget.value?.openGenerateDialog()
}
</script>
```

## Pasos para Completar Integración

### 1. Instalar dependencias PrimeVue (si no están)
```bash
npm install primevue @primevue/themes
```

### 2. Registrar componentes en main.ts
```typescript
// main.ts
import PrimeVue from 'primevue/config'
import Aura from '@primevue/themes/aura'
import AutoComplete from 'primevue/autocomplete'
import Badge from 'primevue/badge'
import Button from 'primevue/button'
// ... etc

app.use(PrimeVue, {
  theme: {
    preset: Aura,
    options: {
      prefix: 'p',
      darkModeSelector: '.dark-theme',
    }
  }
})
```

### 3. Actualizar router para incluir rutas de cursos
```typescript
// router/index.ts
const routes = [
  // ... existing routes
  {
    path: '/courses',
    name: 'courses',
    component: () => import('@/pages/CoursesPage.vue')
  }
]
```

### 4. Agregar imports en componentes que usan cursos
```vue
<script setup lang="ts">
import { useCourseStore } from '@/stores/courseStore'
import { courseProgressService } from '@/services/courseProgressService'
import CourseViewer from '@/components/CourseViewer.vue'
import CourseManagementWidget from '@/components/CourseManagementWidget.vue'
</script>
```

## Notas Importantes

1. **Permisos**: La UI debe respetar los permisos del usuario
   - Solo mostrar botón "Generar Curso" si `courses:create`
   - Solo mostrar panel de revisión si `courses:review`

2. **Estados del curso**: Mostrar indicadores visuales
   - Badge diferente para cada estado (draft, pending, published)
   - Iconos apropiados para acciones

3. **Inicialización de RBAC**: Asegurar que se llame al endpoint `/api/course-rbac/initialize` una vez durante setup

4. **Carga de permisos**: Cargar permisos del usuario al montar componentes que los necesitan

5. **Manejo de errores**: Siempre mostrar mensajes claros cuando fallan llamadas a la API
