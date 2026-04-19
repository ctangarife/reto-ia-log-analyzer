<template>
  <div class="register-container">
    <div class="register-card">
      <div class="register-header">
        <h1>Log Anomaly Detector</h1>
        <p>Crea una nueva cuenta</p>
      </div>

      <form @submit.prevent="handleRegister" class="register-form">
        <div class="form-group">
          <label for="email">Email</label>
          <InputText
            id="email"
            v-model="email"
            type="email"
            placeholder="tu@email.com"
            :disabled="isLoading"
            class="w-full"
            :class="{ 'p-invalid': errors.email }"
            required
          />
          <small v-if="errors.email" class="p-error">{{ errors.email }}</small>
        </div>

        <div class="form-group">
          <label for="username">Usuario</label>
          <InputText
            id="username"
            v-model="username"
            placeholder="nombre_usuario"
            :disabled="isLoading"
            class="w-full"
            :class="{ 'p-invalid': errors.username }"
            required
          />
          <small v-if="errors.username" class="p-error">{{ errors.username }}</small>
        </div>

        <div class="form-group">
          <label for="full_name">Nombre Completo</label>
          <InputText
            id="full_name"
            v-model="fullName"
            placeholder="Nombre Completo"
            :disabled="isLoading"
            class="w-full"
            :class="{ 'p-invalid': errors.full_name }"
            required
          />
          <small v-if="errors.full_name" class="p-error">{{ errors.full_name }}</small>
        </div>

        <div class="form-group">
          <label for="password">Contraseña</label>
          <Password
            id="password"
            v-model="password"
            placeholder="Mínimo 8 caracteres"
            :disabled="isLoading"
            class="w-full"
            :class="{ 'p-invalid': errors.password }"
            :feedback="true"
            toggleMask
            required
          />
          <small v-if="errors.password" class="p-error">{{ errors.password }}</small>
        </div>

        <div class="form-group">
          <label for="confirm_password">Confirmar Contraseña</label>
          <Password
            id="confirm_password"
            v-model="confirmPassword"
            placeholder="Repite tu contraseña"
            :disabled="isLoading"
            class="w-full"
            :class="{ 'p-invalid': errors.confirm_password }"
            :feedback="false"
            toggleMask
            required
          />
          <small v-if="errors.confirm_password" class="p-error">{{ errors.confirm_password }}</small>
        </div>

        <Message
          v-if="errorMessage"
          severity="error"
          :closable="false"
          class="error-message"
        >
          {{ errorMessage }}
        </Message>

        <Message
          v-if="successMessage"
          severity="success"
          :closable="false"
          class="success-message"
        >
          {{ successMessage }}
        </Message>

        <Button
          type="button"
          label="Registrarse"
          :loading="isLoading"
          class="register-button"
          :disabled="!isFormValid"
          @click="handleRegister"
        />

        <div class="form-footer">
          <p>
            ¿Ya tienes una cuenta?
            <a href="#" @click.prevent="goToLogin" class="link">Inicia sesión</a>
          </p>
        </div>
      </form>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { registerUser } from '../services/authService'
import InputText from 'primevue/inputtext'
import Password from 'primevue/password'
import Button from 'primevue/button'
import Message from 'primevue/message'

const router = useRouter()

const email = ref('')
const username = ref('')
const fullName = ref('')
const password = ref('')
const confirmPassword = ref('')
const isLoading = ref(false)
const errorMessage = ref('')
const successMessage = ref('')
const errors = ref<Record<string, string>>({})

const isFormValid = computed(() => {
  return (
    email.value &&
    username.value &&
    fullName.value &&
    password.value &&
    confirmPassword.value &&
    password.value === confirmPassword.value &&
    password.value.length >= 8
  )
})

function validateForm(): boolean {
  errors.value = {}

  // Validar email
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
  if (!email.value) {
    errors.value.email = 'El email es requerido'
  } else if (!emailRegex.test(email.value)) {
    errors.value.email = 'El email no es válido'
  }

  // Validar username
  if (!username.value) {
    errors.value.username = 'El usuario es requerido'
  } else if (username.value.length < 3) {
    errors.value.username = 'El usuario debe tener al menos 3 caracteres'
  }

  // Validar nombre completo
  if (!fullName.value) {
    errors.value.full_name = 'El nombre completo es requerido'
  }

  // Validar contraseña
  if (!password.value) {
    errors.value.password = 'La contraseña es requerida'
  } else if (password.value.length < 8) {
    errors.value.password = 'La contraseña debe tener al menos 8 caracteres'
  }

  // Validar confirmación de contraseña
  if (!confirmPassword.value) {
    errors.value.confirm_password = 'Confirma tu contraseña'
  } else if (password.value !== confirmPassword.value) {
    errors.value.confirm_password = 'Las contraseñas no coinciden'
  }

  return Object.keys(errors.value).length === 0
}

async function handleRegister() {
  if (!validateForm()) {
    return
  }

  try {
    isLoading.value = true
    errorMessage.value = ''
    successMessage.value = ''

    await registerUser({
      email: email.value,
      username: username.value,
      password: password.value,
      full_name: fullName.value
    })

    successMessage.value = '¡Cuenta creada exitosamente! Redirigiendo al login...'
    
    // Esperar 2 segundos antes de redirigir
    setTimeout(() => {
      goToLogin()
    }, 2000)
  } catch (error: any) {
    console.error('Error en registro:', error)
    
    if (error.response?.status === 409) {
      if (error.response.data?.detail?.includes('email') || error.response.data?.detail?.includes('Email')) {
        errorMessage.value = 'Este email ya está registrado'
        errors.value.email = 'Este email ya está en uso'
      } else if (error.response.data?.detail?.includes('username') || error.response.data?.detail?.includes('Username')) {
        errorMessage.value = 'Este usuario ya está registrado'
        errors.value.username = 'Este usuario ya está en uso'
      } else {
        errorMessage.value = 'El usuario o email ya existe'
      }
    } else if (error.response?.status === 403) {
      errorMessage.value = 'No tienes permisos para crear usuarios. Contacta a un administrador para que te registre.'
    } else if (error.response?.status === 400) {
      const detail = error.response.data?.detail || 'Datos inválidos'
      errorMessage.value = detail
    } else {
      errorMessage.value = error.message || 'Error al crear la cuenta. Intenta nuevamente.'
    }
  } finally {
    isLoading.value = false
  }
}

function goToLogin() {
  router.push({ name: 'login' })
}
</script>

<style scoped>
.register-container {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 100vh;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  padding: 1rem;
}

.register-card {
  background: white;
  border-radius: 12px;
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.1);
  padding: 2.5rem;
  width: 100%;
  max-width: 450px;
}

.register-header {
  text-align: center;
  margin-bottom: 2rem;
}

.register-header h1 {
  margin: 0 0 0.5rem 0;
  color: #2c3e50;
  font-size: 1.75rem;
}

.register-header p {
  margin: 0;
  color: #666;
  font-size: 0.95rem;
}

.register-form {
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
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

.error-message,
.success-message {
  margin: 0;
}

.register-button {
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

:deep(.p-error) {
  color: #e24c4c;
  font-size: 0.85rem;
}
</style>
