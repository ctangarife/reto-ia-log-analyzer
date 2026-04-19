<template>
  <!-- Toast para notificaciones -->
  <Toast />
  <ConfirmDialog />

  <!-- Loading mientras se inicializa -->
  <div v-if="!authStore.isInitialized" class="loading-overlay">
    <ProgressSpinner />
    <p>Iniciando...</p>
  </div>

  <!-- El router decide qué mostrar (Login, Register, o AppLayout con las rutas protegidas) -->
  <router-view v-else />
</template>

<script setup lang="ts">
import { onMounted } from 'vue'
import { useAuthStore } from './stores/authStore'
import ProgressSpinner from 'primevue/progressspinner'
import Toast from 'primevue/toast'
import ConfirmDialog from 'primevue/confirmdialog'

const authStore = useAuthStore()

onMounted(async () => {
  // Inicializar el store desde localStorage
  await authStore.initialize()
})
</script>

<style>
#app {
  min-height: 100vh;
}

.loading-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(255, 255, 255, 0.9);
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  gap: 1rem;
  z-index: 9999;
}

.loading-overlay p {
  color: #64748b;
  font-weight: 500;
}
</style>
