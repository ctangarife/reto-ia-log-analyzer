# Vista de Registro de Usuarios

## Resumen

Se ha implementado una vista de registro de usuarios (`Register.vue`) que permite crear nuevas cuentas en la plataforma.

## Componente Register.vue

### Ubicación
`data/frontend/src/components/Register.vue`

### Funcionalidades

1. **Formulario de Registro**:
   - Email (validación de formato)
   - Usuario (mínimo 3 caracteres)
   - Nombre completo
   - Contraseña (mínimo 8 caracteres)
   - Confirmación de contraseña

2. **Validaciones**:
   - Validación de formato de email
   - Validación de longitud de usuario (mínimo 3 caracteres)
   - Validación de longitud de contraseña (mínimo 8 caracteres)
   - Verificación de coincidencia de contraseñas
   - Mensajes de error específicos por campo

3. **Manejo de Errores**:
   - `409 Conflict`: Usuario o email ya existe
   - `403 Forbidden`: No tiene permisos (requiere super admin)
   - `400 Bad Request`: Datos inválidos
   - Mensajes de error amigables para el usuario

4. **Experiencia de Usuario**:
   - Mensaje de éxito al crear cuenta
   - Redirección automática al login después del registro
   - Enlace para volver al login
   - Estados de carga durante el proceso

## Integración

### Navegación entre Login y Register

- El componente `Login.vue` tiene un enlace "Regístrate" que muestra el formulario de registro
- El componente `Register.vue` tiene un enlace "Inicia sesión" que vuelve al login
- La navegación se maneja mediante eventos Vue (`@go-to-register` y `@go-to-login`)

### Servicio de Autenticación

Se agregó la función `registerUser()` en `authService.ts` que:
- Hace una petición POST a `/api/users`
- Maneja el token JWT opcionalmente (para super admins que crean usuarios)
- Maneja errores específicos de la API

## Consideraciones Importantes

### Permisos según API

Según `doc/API-USUARIOS-CRUD.md`, el endpoint `POST /api/users` requiere permisos de **super administrador**.

**Comportamiento Actual**:
- Si el usuario no está autenticado, intenta registro público
- Si el backend rechaza con 403, muestra mensaje indicando que se necesita un administrador
- Si el usuario está autenticado como super admin, puede crear usuarios directamente

### Posibles Escenarios

1. **Registro Público Permitido**:
   - Si el backend permite registro público (sin autenticación), funcionará directamente
   - El usuario puede registrarse y luego iniciar sesión

2. **Solo Super Admin**:
   - Si el backend requiere autenticación de super admin:
     - Usuarios normales verán mensaje: "No tienes permisos para crear usuarios. Contacta a un administrador."
     - Super admins pueden crear usuarios directamente desde la vista

3. **Registro con Aprobación**:
   - Si el backend implementa registro con aprobación:
     - El usuario se registra pero queda inactivo (`is_active: false`)
     - Un super admin debe activarlo después

## Uso

### Para Usuarios Nuevos

1. Acceder a la aplicación
2. Hacer clic en "Regístrate" en la pantalla de login
3. Completar el formulario de registro
4. Si tiene permisos o el backend permite registro público, la cuenta se crea
5. Redirección automática al login para iniciar sesión

### Para Super Administradores

1. Iniciar sesión como super admin
2. Pueden crear usuarios directamente desde la vista de registro
3. El token JWT se incluye automáticamente en la petición

## Estilos

El componente usa el mismo diseño visual que `Login.vue`:
- Fondo con gradiente
- Tarjeta blanca centrada
- Formulario con campos validados
- Mensajes de error/success destacados
- Enlaces de navegación

## Próximos Pasos (Opcional)

1. **Confirmación por Email**: Si el backend implementa confirmación por email, agregar mensaje informativo
2. **Política de Contraseñas**: Mostrar requisitos de contraseña más detallados
3. **Captcha**: Agregar protección contra bots si es necesario
4. **Términos y Condiciones**: Agregar checkbox de aceptación de términos

---

**Última actualización**: 2026-02-01
**Versión**: 1.0.0
