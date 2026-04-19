<template>
  <div class="learning-view">
    <!-- Empty state - no project selected -->
    <div v-if="!authStore.selectedProjectId" class="empty-selection">
      <i class="pi pi-folder-open text-4xl"></i>
      <p>Selecciona un proyecto para acceder al curso</p>
    </div>

    <!-- Course content with tabs -->
    <template v-else>
      <!-- Course Status Tabs -->
      <TabView v-model:activeIndex="activeTab" class="course-tabs">
        <!-- Published Course Tab (Default) -->
        <TabPanel header="📖 Publicado">
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

          <!-- No hay curso publicado -->
          <div v-if="!courseProgress || courseProgress.total_modules === 0" class="no-course-state">
            <i class="pi pi-bookmark" style="font-size: 3rem; color: #cbd5e1;"></i>
            <h3>No hay curso publicado</h3>
            <p>Este proyecto aún no tiene un curso de aprendizaje disponible.</p>
            <p class="hint">Los creadores de contenido pueden generar cursos desde la pestaña "Borradores".</p>
          </div>

          <!-- Contenido del curso -->
          <div v-else class="course-content">
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
                      <!-- Mostrar contenido markdown EXCEPTO para exámenes de nuevo formato -->
                      <div v-if="!isNewExamFormat(lesson)" class="lesson-text" v-html="renderMarkdown(lesson.content)"></div>

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
                              <pre class="anomaly-log">{{ anomaly.log_entry || 'Sin datos' }}</pre>
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

                        <!-- Examen final - Nuevo formato con opciones múltiples -->
                        <div v-if="lesson.exercise_data?.type === 'final_exam' && isNewExamFormat(lesson)" class="final-exam">
                          <p class="exam-intro">
                            <strong>Examen Final - Opción Múltiple</strong><br>
                            Responde cada pregunta seleccionando la opción correcta.
                            Necesitas al menos {{ lesson.exercise_data.passing_score || 70 }}% para aprobar.
                            Cada pregunta vale 5 puntos (10 preguntas × 5 pts = 50 pts total).
                          </p>

                          <div v-if="examQuestions.length > 0" class="exam-questions-new">
                            <div
                              v-for="(question, qIdx) in examQuestions"
                              :key="qIdx"
                              class="exam-question-new"
                            >
                              <div class="question-header">
                                <h5>Anomalía {{ question.anomalyIndex }} - Pregunta {{ question.questionIndex }}</h5>
                                <span class="question-type">{{ question.anomalyType }}</span>
                              </div>

                              <pre class="exam-log">{{ question.logEntry }}</pre>

                              <p class="question-text">{{ question.question }}</p>

                              <!-- Opciones de respuesta -->
                              <div v-if="!examResults" class="options-grid">
                                <button
                                  v-for="option in question.options"
                                  :key="option.letter"
                                  class="option-button"
                                  :class="{ selected: examAnswers[qIdx]?.selected === option.letter }"
                                  @click="selectExamOption(qIdx, option.letter)"
                                  :disabled="!!examResults"
                                >
                                  <span class="option-letter">{{ option.letter }}</span>
                                  <span class="option-text">{{ option.text }}</span>
                                </button>
                              </div>

                              <!-- Resultado por pregunta -->
                              <div v-if="examResults?.questionResults?.[qIdx]" class="question-result">
                                <Tag :value="examResults.questionResults[qIdx].correct ? 'Correcto ✓' : 'Incorrecto ✗'"
                                     :severity="examResults.questionResults[qIdx].correct ? 'success' : 'danger'" />
                                <span v-if="!examResults.questionResults[qIdx].correct" class="correct-answer">
                                  Correcta: {{ examResults.questionResults[qIdx].correctAnswer }}
                                </span>
                              </div>
                            </div>
                          </div>

                          <!-- Botón enviar -->
                          <div v-if="!examResults" class="exam-actions">
                            <button class="btn-submit" @click="submitExam(lesson)" :disabled="!allExamAnswers || examSubmitting">
                              {{ examSubmitting ? 'Enviando...' : 'Enviar Examen' }}
                            </button>
                          </div>

                          <!-- Resultados generales -->
                          <div v-if="examResults" class="exam-results">
                            <div :class="['result-banner', examResults.passed ? 'success' : 'error']">
                              <i :class="examResults.passed ? 'pi-check-circle' : 'pi-times-circle'"></i>
                              <div>
                                <strong>{{ examResults.passed ? '¡Aprobado!' : 'No Aprobado' }}</strong>
                                <p>{{ examResults.feedback }}</p>
                              </div>
                            </div>
                            <div class="score-display">
                              <div class="score-circle" :class="{ passed: examResults.passed }">
                                <span class="score-number">{{ examResults.score }}%</span>
                                <span class="score-label">de {{ examResults.passingScore }}% requerido</span>
                              </div>
                            </div>
                          </div>
                        </div>

                        <!-- Examen final - Formato viejo (tipo + severidad) -->
                        <div v-else-if="lesson.exercise_data?.type === 'final_exam'" class="final-exam">
                          <p class="exam-intro">
                            <strong>Examen Final</strong><br>
                            Analiza cada anomalía e identifica su <strong>tipo</strong> y <strong>severidad</strong>.
                            Necesitas al menos {{ lesson.exercise_data.passing_score || 70 }}% para aprobar.
                            Cada respuesta vale 20 puntos (10 por tipo, 10 por severidad).
                          </p>
                          <div v-if="finalExamAnomalies.length > 0" class="exam-questions">
                            <div
                              v-for="(anomaly, idx) in finalExamAnomalies"
                              :key="idx"
                              class="exam-question"
                            >
                              <div class="exam-question-header">
                                <h5>Pregunta {{ idx + 1 }}</h5>
                                <Tag v-if="finalExamResults?.results[idx]" :value="`${finalExamResults.results[idx].points}/20 pts`" :severity="finalExamResults.results[idx].points >= 15 ? 'success' : finalExamResults.results[idx].points >= 10 ? 'warn' : 'danger'" />
                              </div>
                              <pre class="exam-log">{{ anomaly.log_entry }}</pre>

                              <!-- Formulario de respuestas -->
                              <div v-if="!finalExamResults" class="exam-answer-form">
                                <div class="form-group">
                                  <label>Tipo de Anomalía:</label>
                                  <div class="exam-options">
                                    <button
                                      v-for="option in getExamTypeOptions()"
                                      :key="option.value"
                                      class="exam-option"
                                      :class="{ selected: finalExamAnswers[idx]?.anomaly_type === option.value }"
                                      @click="updateFinalAnswer(idx, 'anomaly_type', option.value)"
                                    >
                                      {{ option.label }}
                                    </button>
                                  </div>
                                </div>
                                <div class="form-group">
                                  <label>Severidad:</label>
                                  <div class="exam-options">
                                    <button
                                      v-for="option in getExamSeverityOptions()"
                                      :key="option.value"
                                      class="exam-option severity-option"
                                      :class="{ selected: finalExamAnswers[idx]?.severity === option.value }"
                                      @click="updateFinalAnswer(idx, 'severity', option.value)"
                                    >
                                      {{ option.label }}
                                    </button>
                                  </div>
                                </div>
                              </div>

                              <!-- Resultados por pregunta -->
                              <div v-if="finalExamResults?.results[idx]" class="exam-question-result">
                                <div class="result-details">
                                  <div class="result-item" :class="{ correct: finalExamResults.results[idx].is_correct_type }">
                                    <i :class="finalExamResults.results[idx].is_correct_type ? 'pi-check-circle' : 'pi-times-circle'"></i>
                                    <span>Tipo: <strong>{{ finalExamResults.results[idx].user_type }}</strong> {{ finalExamResults.results[idx].is_correct_type ? '✓' : `✗ (Correcto: ${finalExamResults.results[idx].correct_type})` }}</span>
                                  </div>
                                  <div class="result-item" :class="{ correct: finalExamResults.results[idx].is_correct_severity }">
                                    <i :class="finalExamResults.results[idx].is_correct_severity ? 'pi-check-circle' : 'pi-times-circle'"></i>
                                    <span>Severidad: <strong>{{ finalExamResults.results[idx].user_severity }}</strong> {{ finalExamResults.results[idx].is_correct_severity ? '✓' : `✗ (Correcto: ${finalExamResults.results[idx].correct_severity})` }}</span>
                                  </div>
                                </div>
                              </div>
                            </div>
                          </div>

                          <!-- Botón enviar / reiniciar -->
                          <div v-if="!finalExamResults" class="exam-actions">
                            <button class="btn-submit" @click="submitFinalExam(lesson)" :disabled="!allFinalAnswers || finalExamSubmitting">
                              {{ finalExamSubmitting ? 'Enviando...' : 'Enviar Examen' }}
                            </button>
                          </div>
                          <div v-else class="exam-actions">
                            <button v-if="finalExamResults.can_retake && !finalExamResults.passed" class="btn-retry" @click="resetFinalExam">
                              Intentar de Nuevo
                            </button>
                          </div>

                          <!-- Resultados generales -->
                          <div v-if="finalExamResults" class="exam-results">
                            <div :class="['result-banner', finalExamResults.passed ? 'success' : 'error']">
                              <i :class="finalExamResults.passed ? 'pi-check-circle' : 'pi-times-circle'"></i>
                              <div>
                                <strong>{{ finalExamResults.passed ? '¡Aprobado!' : 'No Aprobado' }}</strong>
                                <p>{{ finalExamResults.feedback }}</p>
                              </div>
                            </div>
                            <div class="score-display">
                              <div class="score-circle" :class="{ passed: finalExamResults.passed }">
                                <span class="score-number">{{ finalExamResults.score }}%</span>
                                <span class="score-label">de {{ finalExamResults.passing_score }}% requerido</span>
                              </div>
                            </div>
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
        </TabPanel>

        <!-- Draft Courses Tab (for creators) -->
        <TabPanel header="📝 Borradores" v-if="canManageCourses">
          <DraftCoursesPanel
            ref="draftPanelRef"
            :workspaceId="authStore.selectedWorkspaceId"
            :projectId="authStore.selectedProjectId"
            @course-selected="onCourseSelected"
            @course-actioned="onCourseActioned"
            @course-generated="onCourseGenerated"
          />
        </TabPanel>

        <!-- Pending Courses Tab (for reviewers) -->
        <TabPanel header="⏳ Pendientes" v-if="canReviewCourses">
          <PendingCoursesPanel
            ref="pendingPanelRef"
            :workspaceId="authStore.selectedWorkspaceId"
            :projectId="authStore.selectedProjectId"
            @course-selected="onCourseSelected"
            @course-actioned="onCourseActioned"
          />
        </TabPanel>

        <!-- Approved Courses Tab (ready to publish) -->
        <TabPanel header="✅ Aprobados" v-if="canManageCourses">
          <ApprovedCoursesPanel
            ref="approvedPanelRef"
            :workspaceId="authStore.selectedWorkspaceId"
            :projectId="authStore.selectedProjectId"
            @course-selected="onCourseSelected"
            @course-actioned="onCourseActioned"
          />
        </TabPanel>

        <!-- Archived Courses Tab -->
        <TabPanel header="📦 Archivados" v-if="canManageCourses">
          <ArchivedCoursesPanel
            ref="archivedPanelRef"
            :workspaceId="authStore.selectedWorkspaceId"
            :projectId="authStore.selectedProjectId"
            @course-republished="onCourseActioned"
          />
        </TabPanel>
      </TabView>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useAuthStore } from '../stores/authStore'
import { useAnalysisStore } from '../stores/analysisStore'
import { useCourseStore } from '../stores/courseStore'
import { courseService } from '../services/courseService'
import { courseProgressService } from '../services/courseProgressService'
import CourseManagementWidget from '../components/CourseManagementWidget.vue'
import DraftCoursesPanel from '../components/DraftCoursesPanel.vue'
import PendingCoursesPanel from '../components/PendingCoursesPanel.vue'
import ApprovedCoursesPanel from '../components/ApprovedCoursesPanel.vue'
import ArchivedCoursesPanel from '../components/ArchivedCoursesPanel.vue'
import Tag from 'primevue/tag'
import ProgressBar from 'primevue/progressbar'
import TabView from 'primevue/tabview'
import TabPanel from 'primevue/tabpanel'
import { marked } from 'marked'
import DOMPurify from 'dompurify'
import type { FinalExamAnswer, FinalExamValidationResponse } from '../services/courseProgressService'

const authStore = useAuthStore()
const analysisStore = useAnalysisStore()
const courseStore = useCourseStore()

// Estado
const courseProgress = ref<any>(null)
const expandedModules = ref<Set<string>>(new Set())
const selectedLesson = ref<any>(null)
const answers = ref<Record<string, number>>({})
const exerciseResults = ref<any>(null)
const projectExercises = ref<any[]>([])
const finalExamAnomalies = ref<any[]>([])
const finalExamAnswers = ref<Record<number, FinalExamAnswer>>({})
const finalExamResults = ref<FinalExamValidationResponse | null>(null)
const finalExamSubmitting = ref(false)

// New exam format (multiple choice)
interface ExamQuestion {
  anomalyIndex: number
  questionIndex: number
  anomalyType: string
  logEntry: string
  question: string
  options: Array<{ letter: string; text: string; correct: boolean }>
  correctAnswer: string
}

interface ExamAnswer {
  selected: string
}

const examQuestions = ref<ExamQuestion[]>([])
const examAnswers = ref<Record<number, ExamAnswer>>({})
const examResults = ref<any>(null)
const examSubmitting = ref(false)

const workspaceUsers = ref<Array<any>>([])
const activeTab = ref(0) // Default to Published tab

// Panel references for tab change reloading
const draftPanelRef = ref<any>(null)
const pendingPanelRef = ref<any>(null)
const approvedPanelRef = ref<any>(null)
const archivedPanelRef = ref<any>(null)

const circumference = 2 * Math.PI * 16

const strokeDashoffset = computed(() => {
  const progress = courseProgress.value?.progress_percentage || 0
  return circumference - (progress / 100) * circumference
})

const hasAnswers = computed(() => Object.keys(answers.value).length > 0)
const allFinalAnswers = computed(() => {
  return finalExamAnomalies.value.length > 0 &&
    finalExamAnomalies.value.every((_, idx) => finalExamAnswers.value[idx]?.anomaly_type && finalExamAnswers.value[idx]?.severity)
})

// New exam format computed
const allExamAnswers = computed(() => {
  return examQuestions.value.length > 0 &&
    examQuestions.value.every((_, idx) => examAnswers.value[idx]?.selected)
})

const canManageCourses = computed(() => {
  return courseStore.canGenerateCourse || courseStore.canReviewCourses
})

const canReviewCourses = computed(() => {
  return courseStore.canReviewCourses
})

// Cargar progreso del curso
async function loadCourseProgress() {
  if (!authStore.selectedProjectId) return

  try {
    courseProgress.value = await courseService.getProgress(authStore.selectedProjectId)

    if (courseProgress.value.modules?.length > 0) {
      expandedModules.value.add(courseProgress.value.modules[0].id)
    }

    // Cargar usuarios del workspace para gestión
    if (authStore.selectedWorkspaceId && canManageCourses.value) {
      await loadWorkspaceUsers()
    }
  } catch (error: any) {
    console.error('Error loading course progress:', error)
  }
}

async function loadWorkspaceUsers() {
  try {
    // TODO: Implementar carga de usuarios del workspace
    // Por ahora solo un array vacío
  } catch (error) {
    console.error('Error loading workspace users:', error)
  }
}

function selectLesson(lesson: any) {
  selectedLesson.value = lesson
  exerciseResults.value = null
  answers.value = {}
  finalExamAnswers.value = {}
  finalExamResults.value = null
  examAnswers.value = {}
  examResults.value = null

  console.log('selectLesson:', lesson.title, 'exercise_data:', lesson.exercise_data)

  if (lesson.exercise_data?.dynamic && lesson.exercise_data.type === 'project_anomalies') {
    console.log('Loading project exercises for lesson:', lesson.id)
    loadProjectExercises(lesson.id)
  } else if (lesson.exercise_data?.type === 'final_exam') {
    console.log('Loading final exam for lesson:', lesson.id)
    // Check if new format (multiple choice)
    if (isNewExamFormat(lesson)) {
      console.log('New exam format detected - loading questions')
      loadExamQuestions(lesson)
    } else {
      console.log('Old exam format - loading from backend')
      loadFinalExam(lesson.id)
    }
  }
}

async function loadProjectExercises(lessonId: string) {
  try {
    console.log('loadProjectExercises called with lessonId:', lessonId, 'projectId:', authStore.selectedProjectId)

    if (!authStore.selectedProjectId) {
      console.error('ERROR: authStore.selectedProjectId is undefined or null!')
      console.error('authStore:', authStore)
      return
    }

    console.log('Calling courseService.getExercises with:', authStore.selectedProjectId, lessonId, 5)
    const data = await courseService.getExercises(authStore.selectedProjectId, lessonId, 5)
    console.log('loadProjectExercises response:', data)
    projectExercises.value = data.exercises || []
    console.log('projectExercises.value:', projectExercises.value)
  } catch (error) {
    console.error('Error loading project exercises:', error)
    console.error('Error details:', error)
  }
}

async function loadFinalExam(lessonId: string) {
  try {
    console.log('loadFinalExam called with lessonId:', lessonId, 'projectId:', authStore.selectedProjectId)

    if (!authStore.selectedProjectId) {
      console.error('ERROR: authStore.selectedProjectId is undefined or null!')
      console.error('authStore:', authStore)
      return
    }

    console.log('Calling courseService.getExercises with:', authStore.selectedProjectId, lessonId, 5)
    const data = await courseService.getExercises(authStore.selectedProjectId, lessonId, 5)
    console.log('loadFinalExam response:', data)

    // For final exam, use the anomaly_ids from the lesson's exercise_data directly
    // The exercise_data.anomalies contains the correct chunk_ids
    const lessonExerciseAnomalies = selectedLesson.value?.exercise_data?.anomalies || []
    const exercises = data.exercises || []

    finalExamAnomalies.value = exercises.map((ex: any, idx: number) => ({
      ...ex,
      // Override anomaly_id with the correct chunk_id from exercise_data
      anomaly_id: lessonExerciseAnomalies[idx]?.id || ex.anomaly_id
    }))

    console.log('finalExamAnomalies.value:', finalExamAnomalies.value)

    // Initialize empty answers for each anomaly
    finalExamAnomalies.value.forEach((anomaly: any, idx: number) => {
      if (!finalExamAnswers.value[idx]) {
        finalExamAnswers.value[idx] = {
          anomaly_id: anomaly.anomaly_id || '',
          anomaly_type: '',
          severity: '',
          action: ''
        }
      }
    })
  } catch (error) {
    console.error('Error loading final exam:', error)
  }
}

function toggleModule(moduleId: string) {
  if (expandedModules.value.has(moduleId)) {
    expandedModules.value.delete(moduleId)
  } else {
    expandedModules.value.add(moduleId)
  }
}

function getExamTypeOptions() {
  return [
    { value: 'Seguridad', label: '🔴 Seguridad' },
    { value: 'Performance', label: '🟡 Performance' },
    { value: 'Red', label: '🟠 Red' },
    { value: 'Comportamiento', label: '🟠 Comportamiento' },
    { value: 'General', label: '⚪ General' }
  ]
}

function getExamSeverityOptions() {
  return [
    { value: 'Critical', label: '🔴 Crítica' },
    { value: 'High', label: '🟠 Alta' },
    { value: 'Medium', label: '🟡 Media' },
    { value: 'Low', label: '🟢 Baja' }
  ]
}

function updateFinalAnswer(questionIndex: number, field: 'anomaly_type' | 'severity' | 'action', value: string) {
  if (!finalExamAnswers.value[questionIndex]) {
    finalExamAnswers.value[questionIndex] = {
      anomaly_id: finalExamAnomalies.value[questionIndex]?.anomaly_id || '',
      anomaly_type: '',
      severity: '',
      action: ''
    }
  }
  finalExamAnswers.value[questionIndex][field] = value
}

async function submitFinalExam(lesson: any) {
  if (!authStore.selectedProjectId) return

  finalExamSubmitting.value = true
  try {
    // Prepare answers array
    const answersArray = finalExamAnomalies.value.map((anomaly, idx) => ({
      anomaly_id: anomaly.anomaly_id,
      anomaly_type: finalExamAnswers.value[idx]?.anomaly_type || '',
      severity: finalExamAnswers.value[idx]?.severity || '',
      action: finalExamAnswers.value[idx]?.action || 'Analizar y documentar'
    }))

    const result = await courseProgressService.submitFinalExam(
      authStore.selectedProjectId,
      {
        lesson_id: lesson.id,
        answers: answersArray
      }
    )

    finalExamResults.value = result

    if (result.passed) {
      await completeLessonWithScore(lesson, result.score)
    }
  } catch (error: any) {
    console.error('Error submitting final exam:', error)
    alert('Error al enviar el examen: ' + (error.response?.data?.detail || error.message))
  } finally {
    finalExamSubmitting.value = false
  }
}

function resetFinalExam() {
  finalExamAnswers.value = {}
  finalExamResults.value = null
}

// ==================== NEW EXAM FORMAT FUNCTIONS ====================

// Check if lesson has new exam format (multiple choice)
function isNewExamFormat(lesson: any): boolean {
  return lesson.exercise_data?.questions_by_anomaly &&
    Array.isArray(lesson.exercise_data.questions_by_anomaly) &&
    lesson.exercise_data.questions_by_anomaly.length > 0 &&
    lesson.exercise_data.questions_by_anomaly[0]?.questions?.[0]?.options
}

// Load questions for new exam format
function loadExamQuestions(lesson: any) {
  examQuestions.value = []
  examAnswers.value = {}
  examResults.value = null

  const questionsByAnomaly = lesson.exercise_data?.questions_by_anomaly || []

  questionsByAnomaly.forEach((qba: any) => {
    qba.questions.forEach((q: any, qIdx: number) => {
      if (q.question && q.options) {
        const correctOption = q.options.find((o: any) => o.correct)
        examQuestions.value.push({
          anomalyIndex: qba.index,
          questionIndex: qIdx + 1,
          anomalyType: qba.type,
          logEntry: qba.log_entry || '',
          question: q.question,
          options: q.options,
          correctAnswer: correctOption?.letter || ''
        })
      }
    })
  })
}

// Select an option for new exam format
function selectExamOption(questionIdx: number, letter: string) {
  examAnswers.value[questionIdx] = { selected: letter }
}

// Submit new exam format
async function submitExam(lesson: any) {
  if (!authStore.selectedProjectId) return

  examSubmitting.value = true

  try {
    // Grade locally since we have the correct answers
    let correctCount = 0
    const questionResults: any[] = []

    examQuestions.value.forEach((q, idx) => {
      const selected = examAnswers.value[idx]?.selected
      const isCorrect = selected === q.correctAnswer

      if (isCorrect) correctCount++

      questionResults.push({
        question: q.question,
        selected: selected,
        correctAnswer: q.correctAnswer,
        correct: isCorrect
      })
    })

    const score = Math.round((correctCount / examQuestions.value.length) * 100)
    const passingScore = lesson.exercise_data?.passing_score || 70
    const passed = score >= passingScore

    examResults.value = {
      score,
      passingScore,
      passed,
      feedback: passed
        ? '¡Excelente! Has demostrado un buen entendimiento de las anomalías.'
        : 'Necesitas repasar algunos conceptos. Intenta nuevamente.',
      questionResults,
      canRetake: true
    }

    // Mark lesson complete if passed
    if (passed) {
      await completeLessonWithScore(lesson, score)
    }
  } catch (error: any) {
    console.error('Error submitting exam:', error)
    alert('Error al enviar el examen')
  } finally {
    examSubmitting.value = false
  }
}

// Reset new exam format
function resetExam() {
  examAnswers.value = {}
  examResults.value = null
}

function selectAnswer(questionId: string, optionIndex: number) {
  answers.value[questionId] = optionIndex
}

async function submitExercise(lesson: any) {
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

function resetExercise() {
  exerciseResults.value = null
  answers.value = {}
}

async function completeLessonWithScore(lesson: any, score?: number) {
  try {
    await courseService.completeLesson(authStore.selectedProjectId!, lesson.id, score)

    lesson.is_completed = true
    lesson.completed_at = new Date().toISOString()

    await loadCourseProgress()
  } catch (error: any) {
    console.error('Error completing lesson:', error)
    alert('Error al completar la lección')
  }
}

function renderMarkdown(content: string) {
  const rawHtml = marked(content)
  return DOMPurify.sanitize(rawHtml, {
    ALLOWED_TAGS: ['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'strong', 'em', 'br', 'ul', 'ol', 'li', 'code', 'pre', 'blockquote', 'a', 'hr'],
    ALLOWED_ATTR: ['href', 'title', 'class', 'target'],
    ALLOW_DATA_ATTR: false,
    ALLOW_UNKNOWN_PROTOCOLS: false
  })
}

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

async function downloadCertificate() {
  try {
    const cert = await courseService.getCertificate(authStore.selectedProjectId!)
    const certHTML = generateCertificateHTML(cert)

    // Open in new window for printing/saving as PDF
    const printWindow = window.open('', '_blank')
    if (printWindow) {
      printWindow.document.write(certHTML)
      printWindow.document.close()
      setTimeout(() => {
        printWindow.focus()
        printWindow.print()
      }, 250)
    }
  } catch (error) {
    console.error('Error downloading certificate:', error)
  }
}

function generateCertificateHTML(cert: any) {
  const projectName = getProjectName(authStore.selectedProjectId)
  const userName = authStore.user?.username || authStore.user?.email || 'Usuario'
  const date = new Date(cert.issued_at).toLocaleDateString('es-ES', {
    year: 'numeric',
    month: 'long',
    day: 'numeric'
  })

  return `
<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <title>Certificado - LogsAnomaly</title>
  <style>
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body {
      font-family: 'Georgia', serif;
      background: #f5f5f5;
      display: flex;
      justify-content: center;
      align-items: center;
      min-height: 100vh;
      padding: 20px;
    }
    .certificate {
      background: white;
      width: 210mm;
      min-height: 297mm;
      padding: 40px;
      border: 10px solid #667eea;
      position: relative;
      box-shadow: 0 10px 40px rgba(0,0,0,0.1);
    }
    .certificate::before {
      content: '';
      position: absolute;
      top: 10px;
      left: 10px;
      right: 10px;
      bottom: 10px;
      border: 2px solid #764ba2;
    }
    .header {
      text-align: center;
      margin-bottom: 30px;
    }
    .logo {
      font-size: 24px;
      font-weight: bold;
      color: #667eea;
      margin-bottom: 10px;
    }
    .title {
      font-size: 28px;
      color: #333;
      margin-bottom: 30px;
    }
    .content {
      text-align: center;
      line-height: 1.8;
      color: #555;
    }
    .content p {
      margin-bottom: 20px;
    }
    .user-name {
      font-size: 24px;
      font-weight: bold;
      color: #333;
      margin: 20px 0;
    }
    .course-name {
      font-size: 18px;
      font-style: italic;
      color: #667eea;
      margin-bottom: 30px;
    }
    .footer {
      margin-top: 40px;
      text-align: center;
      font-size: 12px;
      color: #999;
    }
    .badge {
      display: inline-block;
      margin: 20px 0;
      font-size: 40px;
    }
  </style>
</head>
<body>
  <div class="certificate">
    <div class="header">
      <div class="logo">LogsAnomaly</div>
      <div class="title">CERTIFICADO DE COMPLETACIÓN</div>
    </div>

    <div class="content">
      <p>Este certifica que</p>
      <div class="user-name">${userName}</div>

      <p>Ha completado satisfactoriamente el curso</p>
      <div class="course-name">"Interpretación de Logs y Detección de Anomalías"</div>

      <p><strong>Proyecto:</strong> ${projectName}</p>
      <p><strong>Fecha de finalización:</strong> ${date}</p>

      <div class="badge">🏆</div>

      <p>Emitido por LogsAnomaly v2.0</p>
    </div>

    <div class="footer">
      Certificado ID: ${authStore.selectedProjectId}_${cert.issued_at}
    </div>
  </div>
</body>
</html>
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

function onCourseGenerated() {
  loadCourseProgress()
  // Cambiar al tab de Publicados para ver el curso
  activeTab.value = 0
}

function onCourseActioned() {
  loadCourseProgress()
}

function onCourseSelected(course: any) {
  // Handle course selection from panel
  console.log('Course selected:', course)
  // Could open a dialog to view course content
}

watch(() => authStore.selectedProjectId, async (newProjectId) => {
  if (newProjectId) {
    await loadCourseProgress()
  }
}, { immediate: true })

// Watch tab changes to reload course lists
watch(activeTab, (newTab) => {
  // Tab 0: Published (no reload needed, handled by selectedProjectId watch)
  // Tab 1: Draft
  if (newTab === 1 && draftPanelRef.value) {
    draftPanelRef.value.loadCourses?.()
  }
  // Tab 2: Pending
  else if (newTab === 2 && pendingPanelRef.value) {
    pendingPanelRef.value.loadCourses?.()
  }
  // Tab 3: Approved
  else if (newTab === 3 && approvedPanelRef.value) {
    approvedPanelRef.value.loadCourses?.()
  }
  // Tab 4: Archived
  else if (newTab === 4 && archivedPanelRef.value) {
    archivedPanelRef.value.loadCourses?.()
  }
})

onMounted(() => {
  loadCourseProgress()
})

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

.empty-selection {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 300px;
  gap: 1rem;
  color: #94a3b8;
}

.empty-selection i {
  color: #cbd5e1;
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

.exam-question-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1rem;
}

.exam-question-header h5 {
  margin: 0;
  color: #334155;
}

.exam-answer-form {
  margin-top: 1rem;
}

.form-group {
  margin-bottom: 1.5rem;
}

.form-group label {
  display: block;
  font-weight: 500;
  margin-bottom: 0.5rem;
  color: #475569;
}

.severity-option {
  grid-template-columns: repeat(4, 1fr);
}

.exam-question-result {
  margin-top: 1rem;
  padding: 1rem;
  background: #f8fafc;
  border-radius: 8px;
}

.result-details {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.result-item {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem;
  border-radius: 4px;
}

.result-item.correct {
  background: #ecfdf5;
  color: #166534;
}

.result-item:not(.correct) {
  background: #fef2f2;
  color: #991b1b;
}

.exam-actions {
  display: flex;
  justify-content: center;
  gap: 1rem;
  margin-top: 1.5rem;
}

.score-display {
  display: flex;
  justify-content: center;
  margin-top: 1.5rem;
}

.score-circle {
  width: 150px;
  height: 150px;
  border-radius: 50%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  border: 8px solid #cbd5e1;
  background: white;
}

.score-circle.passed {
  border-color: #10b981;
  background: linear-gradient(135deg, #ecfdf5 0%, #d1fae5 100%);
}

.score-number {
  font-size: 2.5rem;
  font-weight: bold;
  color: #1e293b;
}

.score-label {
  font-size: 0.85rem;
  color: #64748b;
}

.exam-results {
  margin-top: 1.5rem;
  text-align: center;
}

.no-course-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 4rem 2rem;
  gap: 1rem;
  text-align: center;
  background: white;
  border-radius: 12px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.no-course-state h3 {
  margin: 0;
  color: #475569;
}

.no-course-state p {
  margin: 0;
  color: #94a3b8;
}

.no-course-state .hint {
  font-size: 0.9rem;
  color: #cbd5e1;
  font-style: italic;
}

/* Course Tabs */
.course-tabs {
  margin-top: 1rem;
}

.course-tabs :deep(.p-tabview-nav) {
  background: white;
  border-bottom: 2px solid #e2e8f0;
  padding: 0 1rem;
}

.course-tabs :deep(.p-tabview-nav li) {
  margin-right: 0.5rem;
}

.course-tabs :deep(.p-tabview-nav li .p-tabview-nav-link) {
  background: transparent;
  border: none;
  border-bottom: 3px solid transparent;
  color: #64748b;
  font-weight: 500;
  padding: 1rem 1.5rem;
  transition: all 0.2s;
}

.course-tabs :deep(.p-tabview-nav li .p-tabview-nav-link:hover) {
  background: #f8fafc;
  color: #475569;
}

.course-tabs :deep(.p-tabview-nav li.p-highlight .p-tabview-nav-link) {
  background: transparent;
  border-bottom-color: #667eea;
  color: #667eea;
}

.course-tabs :deep(.p-tabview-panels) {
  background: transparent;
  padding: 1rem 0;
}

/* New Exam Format Styles */
.exam-questions-new {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
  margin-top: 1rem;
}

.exam-question-new {
  background: white;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 1.5rem;
}

.question-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1rem;
}

.question-header h5 {
  margin: 0;
  color: #334155;
}

.question-type {
  font-size: 0.8rem;
  padding: 0.25rem 0.75rem;
  background: #f1f5f9;
  color: #64748b;
  border-radius: 12px;
}

.question-text {
  font-size: 1rem;
  color: #475569;
  margin: 1rem 0;
  line-height: 1.6;
}

.options-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: 0.75rem;
}

.option-button {
  display: flex;
  align-items: center;
  gap: 1rem;
  padding: 1rem;
  border: 2px solid #e2e8f0;
  border-radius: 8px;
  background: white;
  cursor: pointer;
  transition: all 0.2s;
  text-align: left;
}

.option-button:hover:not(:disabled) {
  border-color: #cbd5e1;
  background: #f8fafc;
}

.option-button.selected {
  border-color: #667eea;
  background: #f0f4ff;
}

.option-button:disabled {
  cursor: not-allowed;
}

.option-letter {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  background: #f1f5f9;
  color: #64748b;
  border-radius: 50%;
  font-weight: 600;
  flex-shrink: 0;
}

.option-button.selected .option-letter {
  background: #667eea;
  color: white;
}

.option-text {
  flex: 1;
  color: #475569;
}

.question-result {
  display: flex;
  align-items: center;
  gap: 1rem;
  margin-top: 1rem;
  padding: 0.75rem 1rem;
  background: #f8fafc;
  border-radius: 6px;
}

.correct-answer {
  color: #64748b;
  font-size: 0.9rem;
}
</style>
