import api from './api'

export interface JobResult {
  id: string
  fileName: string
  totalLogs: number
  anomaliesDetected: number
  timestamp: string
}

export interface ActiveJob {
  id: string
  filename: string
  total_size: number
  total_chunks: number
  chunks_processed: number
  status: string
  progress: number
  started_at: string
  elapsed_seconds: number
  project_id: string | null
}

export interface DeleteResponse {
  message: string
  job_id: string
  chunks_deleted: number
  results_deleted: number
}

export interface ReanalyzeResponse {
  job_id: string
  status: string
  message: string
  total_chunks: number
}

export const jobService = {
  async getActiveJobs(projectId?: string): Promise<ActiveJob[]> {
    const params = projectId ? `?project_id=${projectId}` : ''
    const response = await api.get(`/jobs/active${params}`)
    return response.data
  },

  async deleteJob(jobId: string): Promise<DeleteResponse> {
    const response = await api.delete(`/jobs/${jobId}`)
    return response.data
  },

  async getJobDetails(jobId: string): Promise<any> {
    const response = await api.get(`/reports/${jobId}`)
    return response.data
  },

  async reanalyzeJob(jobId: string): Promise<ReanalyzeResponse> {
    const response = await api.post(`/jobs/${jobId}/reanalyze`)
    return response.data
  }
}
