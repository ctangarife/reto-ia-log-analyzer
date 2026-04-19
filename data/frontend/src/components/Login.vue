<template>
  <div class="login-container">
    <div class="login-card">
      <div class="login-header">
        <h1>Log Anomaly Detector</h1>
        <p>Inicia sesión para continuar</p>
      </div>

      <form @submit.prevent="handleLogin" class="login-form">
        <div class="form-group">
          <label for="username">Usuario o Email</label>
          <InputText
            id="username"
            v-model="username"
            placeholder="Ingresa tu usuario o email"
            :disabled="isLoading"
            class="w-full"
            required
          />
        </div>

        <div class="form-group">
          <label for="password">Contraseña</label>
          <Password
            id="password"
            v-model="password"
            placeholder="Ingresa tu contraseña"
            :disabled="isLoading"
            class="w-full"
            :feedback="false"
            toggleMask
            required
          />
        </div>

        <Message
          v-if="errorMessage"
          severity="error"
          :closable="false"
          class="error-message"
        >
          {{ errorMessage }}
        </Message>

        <Button
          type="submit"
          label="Iniciar Sesión"
          :loading="isLoading"
          class="login-button"
          :disabled="!username || !password"
        />

        <div class="form-footer">
          <p>
            ¿No tienes una cuenta?
            <a href="#" @click.prevent="goToRegister" class="link">Regístrate</a>
          </p>
        </div>
      </form>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/authStore'
import InputText from 'primevue/inputtext'
import Password from 'primevue/password'
import Button from 'primevue/button'
import Message from 'primevue/message'

const router = useRouter()
const authStore = useAuthStore()

const username = ref('')
const password = ref('')
const isLoading = ref(false)
const errorMessage = ref('')

async function handleLogin() {
  if (!username.value || !password.value) {
    errorMessage.value = 'Por favor completa todos los campos'
    return
  }

  try {
    isLoading.value = true
    errorMessage.value = ''

    await authStore.loginUser(username.value, password.value)

    // Redirigir a la aplicación principal
    router.push({ name: 'analysis' })
  } catch (error: any) {
    errorMessage.value = error.message || 'Error al iniciar sesión. Verifica tus credenciales.'
  } finally {
    isLoading.value = false
  }
}

function goToRegister() {
  router.push({ name: 'register' })
}
</script>

<style scoped>
.login-container {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 100vh;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  padding: 1rem;
}

.login-card {
  background: white;
  border-radius: 12px;
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.1);
  padding: 2.5rem;
  width: 100%;
  max-width: 400px;
}

.login-header {
  text-align: center;
  margin-bottom: 2rem;
}

.login-header h1 {
  margin: 0 0 0.5rem 0;
  color: #2c3e50;
  font-size: 1.75rem;
}

.login-header p {
  margin: 0;
  color: #666;
  font-size: 0.95rem;
}

.login-form {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.form-group label {
  font-weight: 500;
  color: #2c3e50;
  font-size: 0.9rem;
}

.error-message {
  margin: 0;
}

.login-button {
  width: 100%;
  padding: 0.75rem;
  font-size: 1rem;
  margin-top: 0.5rem;
}

.form-footer {
  text-align: center;
  margin-top: 1rem;
  padding-top: 1rem;
  border-top: 1px solid #e0e0e0;
}

.form-footer p {
  margin: 0;
  color: #666;
  font-size: 0.9rem;
}

.link {
  color: #667eea;
  text-decoration: none;
  font-weight: 500;
  cursor: pointer;
}

.link:hover {
  text-decoration: underline;
}

:deep(.p-inputtext),
:deep(.p-password) {
  width: 100%;
}
</style>
