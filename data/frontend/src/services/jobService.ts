import api from './api'

export interface JobResult {
  id: string
  fileName: string
  totalLogs: number
  anomaliesDetected: number
  timestamp: string
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
