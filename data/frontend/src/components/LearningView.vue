<template>
  <div class="learning-view">
    <!-- Header del curso -->
    <div class="course-header">
      <div class="header-info">
        <h2>📚 Curso de Interpretación de Logs</h2>
        <p class="project-name">Proyecto: {{ getProjectName(authStore.selectedProjectId) }}</p>
      </div>
      <div class="header-progress">
        <div class="progress-ring" :class="{ completed: courseProgress?.is_completed }">
          <svg viewBox="0 0 36 36">
            <path
              class="progress-ring-circle"
              :stroke-dasharray="circumference + ' ' + circumference"
              :style="{ strokeDashoffset: strokeDashoffset }"
            />
            <text x="18" y="20" text-anchor="middle" class="progress-text">
              {{ Math.round(courseProgress?.progress_percentage || 0) }}%
            </text>
          </svg>
        </div>
      </div>
    </div>

    <!-- Badge de finalización -->
    <div v-if="courseProgress?.is_completed && courseProgress.badge_earned" class="completion-banner">
      <div class="banner-content">
        <div class="banner-icon">🏆</div>
        <div class="banner-text">
          <h3>¡Felicidades! Has completado el curso</h3>
          <p>Has demostrado tu expertise en interpretación de logs.</p>
        </div>
        <div class="banner-actions">
          <button class="btn-download" @click="downloadCertificate">
            📜 Descargar Certificado
          </button>
        </div>
      </div>
    </div>

    <!-- Contenido del curso -->
    <div class="course-content">
      <!-- Lista de módulos -->
      <div class="modules-list">
        <div
          v-for="module in courseProgress?.modules || []"
          :key="module.id"
          class="module-card"
        >
          <div
            class="module-header"
            @click="toggleModule(module.id)"
            :class="{ active: expandedModules.has(module.id) }"
          >
            <div class="module-info">
              <span class="module-number">Módulo {{ module.module_order }}</span>
              <h3>{{ module.title }}</h3>
              <p v-if="module.description">{{ module.description }}</p>
            </div>
            <div class="module-stats">
              <span class="progress-badge">
                {{ module.completed_lessons }}/{{ module.total_lessons }} lecciones
              </span>
              <i class="pi" :class="expandedModules.has(module.id) ? 'pi-chevron-up' : 'pi-chevron-down'"></i>
            </div>
          </div>

          <!-- Lecciones del módulo -->
          <div v-show="expandedModules.has(module.id)" class="lessons-list">
            <div
              v-for="lesson in module.lessons"
              :key="lesson.id"
              class="lesson-item"
              :class="{ completed: lesson.is_completed }"
            >
              <div class="lesson-header" @click="selectLesson(lesson)">
                <div class="lesson-info">
                  <i
                    class="pi"
                    :class="lesson.is_completed ? 'pi-check-circle' : 'pi-circle'"
                  ></i>
                  <span class="lesson-number">{{ module.module_order }}.{{ lesson.lesson_order }}</span>
                  <span class="lesson-title">{{ lesson.title }}</span>
                </div>
                <i v-if="lesson.exercise_data" class="pi pi-flag-fill" title="Tiene ejercicio"></i>
              </div>

              <!-- Contenido de la lección (cuando está seleccionada) -->
              <div v-if="selectedLesson?.id === lesson.id" class="lesson-content">
                <div class="lesson-text" v-html="renderMarkdown(lesson.content)"></div>

                <!-- Ejercicio si existe -->
                <div v-if="lesson.exercise_data" class="exercise-section">
                  <h4>📝 Ejercicio Práctico</h4>

                  <!-- Quiz/Analysis estático -->
                  <div v-if="['quiz', 'analysis'].includes(lesson.exercise_data.type) && !exerciseResults">
                    <div class="quiz-container">
                      <div
                        v-for="q in lesson.exercise_data.questions"
                        :key="q.id"
                        class="quiz-question"
                      >
                        <p class="question-text">{{ q.question }}</p>
                        <div class="quiz-options">
                          <button
                            v-for="(option, idx) in q.options"
                            :key="idx"
                            class="quiz-option"
                            :class="{ selected: answers[q.id] === idx, correct: exerciseResults?.correct_answer?.[q.id] === idx }"
                            @click="selectAnswer(q.id, idx)"
                          >
                            {{ option }}
                          </button>
                        </div>
                      </div>
                    </div>
                    <button class="btn-submit" @click="submitExercise(lesson)" :disabled="!hasAnswers">
                      Enviar Respuestas
                    </button>
                  </div>

                  <!-- Resultados del ejercicio -->
                  <div v-if="exerciseResults" class="exercise-results">
                    <div :class="['result-banner', exerciseResults.is_correct ? 'success' : 'error']">
                      <i :class="exerciseResults.is_correct ? 'pi-check-circle' : 'pi-times-circle'"></i>
                      <span>{{ exerciseResults.feedback }}</span>
                    </div>
                    <div v-if="!exerciseResults.is_correct && exerciseResults.correct_answer" class="correct-answer">
                      <h5>Respuestas Correctas:</h5>
                      <ul>
                        <li v-for="(q, idx) in lesson.exercise_data.questions" :key="idx">
                          Pregunta {{ idx + 1 }}: {{ q.options[exerciseResults.correct_answer[q.id]] }}
                        </li>
                      </ul>
                    </div>
                    <div v-if="exerciseResults.explanation" class="explanation">
                      <h5>Explicación:</h5>
                      <p>{{ exerciseResults.explanation }}</p>
                    </div>
                    <button v-if="!exerciseResults.is_correct" class="btn-retry" @click="resetExercise">
                      Intentar de Nuevo
                    </button>
                  </div>

                  <!-- Ejercicios dinámicos del proyecto -->
                  <div v-if="lesson.exercise_data?.type === 'project_anomalies'" class="project-exercises">
                    <p>Analiza las anomalías detectadas en tu proyecto:</p>
                    <div v-if="projectExercises.length > 0" class="anomalies-list">
                      <div
                        v-for="(anomaly, idx) in projectExercises"
                        :key="idx"
                        class="anomaly-card"
                      >
                        <div class="anomaly-header">
                          <span class="anomaly-number">Anomalía #{{ idx + 1 }}</span>
                          <Tag :value="getSeverityText(anomaly.score)" :severity="getSeverityClass(anomaly.score)" />
                        </div>
                        <pre class="anomaly-log">{{ anomaly.log_entry || anomaly.log_entry || 'Sin datos' }}</pre>
                        <div class="anomaly-explanation">
                          <strong>Explicación LLM:</strong>
                          <p>{{ anomaly.explanation }}</p>
                        </div>
                      </div>
                    </div>
                    <ProgressBar v-else mode="indeterminate" />
                    <button class="btn-complete" @click="completeLessonWithScore(lesson)">
                      Marcar Lección como Completada
                    </button>
                  </div>

                  <!-- Examen final -->
                  <div v-if="lesson.exercise_data?.type === 'final_exam'" class="final-exam">
                    <p class="exam-intro">
                      Responde correctamente al menos {{ lesson.exercise_data.passing_score }}% de las preguntas
                      para completar el curso.
                    </p>
                    <div v-if="finalExamAnomalies.length > 0" class="exam-questions">
                      <div
                        v-for="(anomaly, idx) in finalExamAnomalies"
                        :key="idx"
                        class="exam-question"
                      >
                        <h5>Pregunta {{ idx + 1 }}</h5>
                        <pre class="exam-log">{{ anomaly.log_entry }}</pre>
                        <p class="exam-question-text">
                          ¿Qué tipo de anomalía representa este log?
                        </p>
                        <div class="exam-options">
                          <button
                            v-for="option in getExamOptions()"
                            :key="option.value"
                            class="exam-option"
                            :class="{ selected: finalExamAnswers[idx] === option.value, correct: finalExamResults?.correct_answers?.[idx] === option.value }"
                            @click="selectFinalAnswer(idx, option.value)"
                          >
                            {{ option.label }}
                          </button>
                        </div>
                      </div>
                    </div>
                    <button class="btn-submit" @click="submitFinalExam(lesson)" :disabled="!allFinalAnswers">
                      Enviar Examen
                    </button>
                    <div v-if="finalExamResults" class="exam-results">
                      <div :class="['result-banner', finalExamResults.passed ? 'success' : 'error']">
                        <span>{{ finalExamResults.message }}</span>
                      </div>
                      <p>Score: {{ finalExamResults.score }}%</p>
                    </div>
                  </div>
                </div>

                <!-- Botón para completar si no hay ejercicio -->
                <div v-if="!lesson.exercise_data && !lesson.is_completed" class="lesson-actions">
                  <button class="btn-complete" @click="completeLessonWithScore(lesson)">
                    ✅ Marcar como Completada
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useAuthStore } from '../stores/authStore'
import { useAnalysisStore } from '../stores/analysisStore'
import { courseService } from '../services/courseService'
import Tag from 'primevue/tag'
import ProgressBar from 'primevue/progressbar'
import { marked } from 'marked'
import DOMPurify from 'dompurify'

const authStore = useAuthStore()
const analysisStore = useAnalysisStore()

// Estado
const courseProgress = ref<CourseProgress | null>(null)
const expandedModules = ref<Set<string>>(new Set())
const selectedLesson = ref<CourseLesson | null>(null)
const answers = ref<Record<string, number>>({})
const exerciseResults = ref<any>(null)
const projectExercises = ref<any[]>([])
const finalExamAnomalies = ref<any[]>([])
const finalExamAnswers = ref<(number | null)[]>([])
const finalExamResults = ref<any>(null)

const circumference = 2 * Math.PI * 16 // para el radio del círculo de progreso

const strokeDashoffset = computed(() => {
  const progress = courseProgress.value?.progress_percentage || 0
  return circumference - (progress / 100) * circumference
})

const hasAnswers = computed(() => Object.keys(answers.value).length > 0)
const allFinalAnswers = computed(() => finalExamAnswers.value.every(a => a !== null))

// Cargar progreso del curso
async function loadCourseProgress() {
  if (!authStore.selectedProjectId) return

  try {
    courseProgress.value = await courseService.getProgress(authStore.selectedProjectId)

    // Auto-expand first module
    if (courseProgress.value.modules.length > 0) {
      expandedModules.value.add(courseProgress.value.modules[0].id)
    }
  } catch (error: any) {
    console.error('Error loading course progress:', error)
  }
}

// Seleccionar lección
function selectLesson(lesson: CourseLesson) {
  selectedLesson.value = lesson
  exerciseResults.value = null
  answers.value = {}
  finalExamAnswers.value = []

  // Cargar ejercicios dinámicos si es necesario
  if (lesson.exercise_data?.dynamic && lesson.exercise_data.type === 'project_anomalies') {
    loadProjectExercises(lesson.id)
  } else if (lesson.exercise_data?.type === 'final_exam') {
    loadFinalExam(lesson.id)
  }
}

// Cargar ejercicios del proyecto
async function loadProjectExercises(lessonId: string) {
  try {
    const data = await courseService.getExercises(authStore.selectedProjectId!, lessonId, 5)
    projectExercises.value = data.exercises || []
  } catch (error) {
    console.error('Error loading project exercises:', error)
  }
}

// Cargar examen final
async function loadFinalExam(lessonId: string) {
  try {
    const data = await courseService.getExercises(authStore.selectedProjectId!, lessonId, 5)
    finalExamAnomalies.value = data.exercises || []
    finalExamAnswers.value = new Array(data.exercises?.length || 0).fill(null)
  } catch (error) {
    console.error('Error loading final exam:', error)
  }
}

// Toggle módulo
function toggleModule(moduleId: string) {
  if (expandedModules.value.has(moduleId)) {
    expandedModules.value.delete(moduleId)
  } else {
    expandedModules.value.add(moduleId)
  }
}

// Respuestas de examen
function getExamOptions() {
  return [
    { value: 'security', label: '🔴 Anomalía de Seguridad' },
    { value: 'operational', label: '🟡 Anomalía Operativa' },
    { value: 'behavioral', label: '🟠 Anomalía de Comportamiento' },
    { value: 'normal', label: '🟢 Comportamiento Normal' }
  ]
}

function selectFinalAnswer(questionIndex: number, value: number) {
  finalExamAnswers.value[questionIndex] = value
}

// Validar examen final
async function submitFinalExam(lesson: CourseLesson) {
  const correctAnswers: Record<number, number> = {}
  let correctCount = 0

  finalExamAnomalies.value.forEach((anomaly, idx) => {
    const score = parseFloat(anomaly.score || 0)
    // Lógica simplificada para determinar respuesta correcta
    if (score < -0.3) {
      correctAnswers[idx] = 0 // security
    } else if (score < 0) {
      correctAnswers[idx] = 2 // behavioral
    } else {
      correctAnswers[idx] = 3 // normal
    }

    if (finalExamAnswers.value[idx] === correctAnswers[idx]) {
      correctCount++
    }
  })

  const passingScore = lesson.exercise_data?.passing_score || 70
  const score = Math.round((correctCount / finalExamAnomalies.value.length) * 100)
  const passed = score >= passingScore

  finalExamResults.value = {
    passed,
    score,
    message: passed
      ? '¡Felicitaciones! Has aprobado el examen final.'
      : `Necesitas al menos ${passingScore}% para aprobar. Tu score: ${score}%`,
    correct_answers: correctAnswers
  }

  if (passed) {
    await completeLessonWithScore(lesson, score)
  }
}

// Seleccionar respuesta de quiz
function selectAnswer(questionId: string, optionIndex: number) {
  answers.value[questionId] = optionIndex
}

// Enviar ejercicio
async function submitExercise(lesson: CourseLesson) {
  try {
    const result = await courseService.validateExercise(authStore.selectedProjectId!, {
      lesson_id: lesson.id,
      user_answer: answers.value
    })
    exerciseResults.value = result

    if (result.is_correct) {
      await completeLessonWithScore(lesson, 100)
    }
  } catch (error: any) {
    console.error('Error submitting exercise:', error)
    alert('Error al enviar el ejercicio')
  }
}

// Resetear ejercicio
function resetExercise() {
  exerciseResults.value = null
  answers.value = {}
}

// Completar lección
async function completeLessonWithScore(lesson: CourseLesson, score?: number) {
  try {
    await courseService.completeLesson(authStore.selectedProjectId!, lesson.id, score)

    lesson.is_completed = true
    lesson.completed_at = new Date().toISOString()

    // Recargar progreso
    await loadCourseProgress()
  } catch (error: any) {
    console.error('Error completing lesson:', error)
    alert('Error al completar la lección')
  }
}

// Renderizar markdown con sanitización XSS
function renderMarkdown(content: string) {
  const rawHtml = marked(content)
  return DOMPurify.sanitize(rawHtml, {
    ALLOWED_TAGS: ['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'strong', 'em', 'br', 'ul', 'ol', 'li', 'code', 'pre', 'blockquote', 'a', 'hr'],
    ALLOWED_ATTR: ['href', 'title', 'class', 'target'],
    ALLOW_DATA_ATTR: false,
    ALLOW_UNKNOWN_PROTOCOLS: false
  })
}

// Obtener severidad
function getSeverity(score: number) {
  if (score < -0.3) return 'danger'
  if (score < 0) return 'warning'
  return 'success'
}

function getSeverityClass(score: number) {
  if (score < -0.3) return 'danger'
  if (score < 0) return 'warn'
  return 'success'
}

function getSeverityText(score: number) {
  if (score < -0.3) return 'Alta'
  if (score < 0) return 'Media'
  return 'Baja'
}

// Descargar certificado
async function downloadCertificate() {
  try {
    const cert = await courseService.getCertificate(authStore.selectedProjectId!)

    // Crear certificado PDF simple
    const certContent = generateCertificate(cert)
    const blob = new Blob([certContent], { type: 'application/pdf' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `certificado_${authStore.selectedProjectId}.pdf`
    a.click()
    URL.revokeObjectURL(url)
  } catch (error) {
    console.error('Error downloading certificate:', error)
  }
}

function generateCertificate(cert: any) {
  // Certificado simple en texto plano (el frontend puede mejorarse con jsPDF)
  return `
    =====================================================
       CERTIFICADO DE COMPLETACIÓN - LOGSANOMALTY
    =====================================================

    Este certifica que el usuario:
    ${authStore.user?.username || 'Usuario'}

    Ha completado satisfactoriamente el curso:
    "Interpretación de Logs y Detección de Anomalías"

    Proyecto: ${getProjectName(authStore.selectedProjectId)}
    Fecha de finalización: ${new Date(cert.issued_at).toLocaleDateString()}

    Emitido por LogsAnomaly v2.0
    https://github.com/ctangarife/reto-ia-log-analyzer

    =====================================================
  `
}

function getProjectName(projectId: string | null): string {
  if (!authStore.selectedProjectId) return 'N/A'
  for (const wsId in authStore.projects) {
    const project = authStore.projects[wsId]?.find((p: any) => p.project_id === projectId)
    if (project) return project.name
  }
  return 'Proyecto'
}

// Watch para cambios de proyecto
watch(() => authStore.selectedProjectId, async (newProjectId) => {
  if (newProjectId) {
    await loadCourseProgress()
  }
}, { immediate: true })

onMounted(() => {
  loadCourseProgress()
})

// Expose method for parent component to reload
defineExpose({
  loadCourseProgress
})
</script>

<style scoped>
.learning-view {
  padding: 1.5rem;
  max-width: 1200px;
  margin: 0 auto;
}

.course-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 2rem;
  padding: 1.5rem;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border-radius: 12px;
  color: white;
}

.header-info h2 {
  margin: 0 0 0.5rem 0;
  font-size: 1.5rem;
}

.project-name {
  margin: 0;
  opacity: 0.9;
}

.progress-ring {
  width: 80px;
  height: 80px;
}

.progress-ring-circle {
  fill: transparent;
  stroke: rgba(255, 255, 255, 0.3);
  stroke-width: 4;
  transition: stroke-dashoffset 0.35s;
  transform: rotate(-90deg);
  transform-origin: 50% 50%;
}

.progress-text {
  fill: white;
  font-size: 8px;
  font-weight: bold;
}

.progress-ring.completed .progress-ring-circle {
  stroke: #4ade80;
}

/* Banner de completación */
.completion-banner {
  background: linear-gradient(135deg, #10b981 0%, #059669 100%);
  border-radius: 12px;
  padding: 1.5rem;
  margin-bottom: 2rem;
  color: white;
}

.banner-content {
  display: flex;
  align-items: center;
  gap: 1.5rem;
}

.banner-icon {
  font-size: 3rem;
}

.banner-text h3 {
  margin: 0 0 0.5rem 0;
}

.banner-text p {
  margin: 0;
  opacity: 0.9;
}

.btn-download {
  background: white;
  color: #10b981;
  border: none;
  padding: 0.75rem 1.5rem;
  border-radius: 8px;
  font-weight: 600;
  cursor: pointer;
  transition: transform 0.2s;
}

.btn-download:hover {
  transform: scale(1.05);
}

/* Módulos */
.modules-list {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.module-card {
  background: white;
  border-radius: 12px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
  overflow: hidden;
}

.module-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1.5rem;
  cursor: pointer;
  transition: background 0.2s;
}

.module-header:hover {
  background: #f8fafc;
}

.module-header.active {
  background: #eff6ff;
  border-bottom: 1px solid #e2e8f0;
}

.module-info {
  flex: 1;
}

.module-number {
  display: inline-block;
  padding: 0.25rem 0.75rem;
  background: #667eea;
  color: white;
  border-radius: 20px;
  font-size: 0.85rem;
  font-weight: 600;
}

.module-info h3 {
  margin: 0.5rem 0 0.25rem 0;
  font-size: 1.1rem;
}

.module-info p {
  margin: 0;
  color: #64748b;
  font-size: 0.9rem;
}

.module-stats {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.progress-badge {
  padding: 0.25rem 0.75rem;
  background: #e2e8f0;
  border-radius: 20px;
  font-size: 0.85rem;
}

/* Lecciones */
.lessons-list {
  padding: 0 1.5rem 1.5rem;
}

.lesson-item {
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  margin-bottom: 0.75rem;
  overflow: hidden;
}

.lesson-item.completed {
  border-left: 4px solid #10b981;
}

.lesson-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem;
  cursor: pointer;
  transition: background 0.2s;
}

.lesson-header:hover {
  background: #f8fafc;
}

.lesson-info {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.lesson-number {
  color: #94a3b8;
  font-size: 0.85rem;
}

.lesson-title {
  font-weight: 500;
}

.lesson-content {
  padding: 1.5rem;
  background: #f8fafc;
}

.lesson-text {
  line-height: 1.7;
  color: #334155;
}

.lesson-text h1,
.lesson-text h2,
.lesson-text h3 {
  margin-top: 1.5rem;
  margin-bottom: 1rem;
}

.lesson-text pre {
  background: #1e293b;
  color: #e2e8f0;
  padding: 1rem;
  border-radius: 8px;
  overflow-x: auto;
  margin: 1rem 0;
}

.lesson-text code {
  background: #e2e8f0;
  padding: 0.2rem 0.4rem;
  border-radius: 4px;
  font-family: monospace;
}

.lesson-actions {
  margin-top: 1.5rem;
  text-align: right;
}

/* Ejercicios */
.exercise-section {
  margin-top: 2rem;
  padding: 1.5rem;
  background: white;
  border-radius: 8px;
  border: 1px solid #e2e8f0;
}

.exercise-section h4 {
  margin: 0 0 1rem 0;
}

.quiz-question {
  margin-bottom: 1.5rem;
}

.question-text {
  font-weight: 500;
  margin-bottom: 0.75rem;
}

.quiz-options {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.quiz-option {
  padding: 0.75rem 1rem;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  background: white;
  cursor: pointer;
  transition: all 0.2s;
  text-align: left;
}

.quiz-option:hover {
  border-color: #667eea;
  background: #f8fafc;
}

.quiz-option.selected {
  border-color: #667eea;
  background: #eff6ff;
}

.quiz-option.correct {
  border-color: #10b981;
  background: #ecfdf5;
}

/* Resultados */
.exercise-results {
  margin-top: 1.5rem;
}

.result-banner {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 1rem;
  border-radius: 8px;
  margin-bottom: 1rem;
}

.result-banner.success {
  background: #ecfdf5;
  color: #065f46;
}

.result-banner.error {
  background: #fef2f2;
  color: #dc2626;
}

.correct-answer {
  background: #f0fdf4;
  padding: 1rem;
  border-radius: 8px;
  margin-top: 1rem;
}

.correct-answer h5 {
  margin: 0 0 0.5rem 0;
  color: #166534;
}

.explanation {
  background: #eff6ff;
  padding: 1rem;
  border-radius: 8px;
  margin-top: 1rem;
}

.explanation h5 {
  margin: 0 0 0.5rem 0;
  color: #1e40af;
}

/* Botones */
.btn-submit,
.btn-complete,
.btn-retry {
  background: #667eea;
  color: white;
  border: none;
  padding: 0.75rem 1.5rem;
  border-radius: 8px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-submit:hover:not(:disabled),
.btn-complete:hover,
.btn-retry:hover {
  background: #5a67d8;
  transform: translateY(-1px);
}

.btn-submit:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-retry {
  background: #64748b;
}

.btn-retry:hover {
  background: #475569;
}

/* Anomalías del proyecto */
.project-exercises {
  margin-top: 1rem;
}

.anomalies-list {
  display: flex;
  flex-direction: column;
  gap: 1rem;
  margin: 1rem 0;
}

.anomaly-card {
  background: #fef2f2;
  border: 1px solid #fecaca;
  border-radius: 8px;
  padding: 1rem;
}

.anomaly-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1rem;
}

.anomaly-number {
  font-weight: 600;
  color: #991b1b;
}

.anomaly-log {
  background: #1e293b;
  color: #e2e8f0;
  padding: 1rem;
  border-radius: 8px;
  overflow-x: auto;
  font-size: 0.85rem;
  margin-bottom: 1rem;
}

.anomaly-explanation {
  background: white;
  padding: 1rem;
  border-radius: 8px;
}

/* Examen final */
.final-exam {
  margin-top: 1rem;
}

.exam-intro {
  background: #fef3c7;
  padding: 1rem;
  border-radius: 8px;
  border: 1px solid #fde68a;
  margin-bottom: 1.5rem;
}

.exam-question {
  background: white;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 1.5rem;
  margin-bottom: 1.5rem;
}

.exam-log {
  background: #1e293b;
  color: #e2e8f0;
  padding: 1rem;
  border-radius: 8px;
  overflow-x: auto;
  margin: 1rem 0;
}

.exam-question-text {
  font-weight: 500;
  margin: 1.5rem 0 0.75rem 0;
}

.exam-options {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 0.75rem;
}

.exam-option {
  padding: 0.75rem;
  border: 2px solid #e2e8f0;
  border-radius: 8px;
  background: white;
  cursor: pointer;
  transition: all 0.2s;
  text-align: left;
}

.exam-option:hover {
  border-color: #667eea;
}

.exam-option.selected {
  border-color: #667eea;
  background: #eff6ff;
}

.exam-results {
  margin-top: 1.5rem;
  text-align: center;
}
</style>
