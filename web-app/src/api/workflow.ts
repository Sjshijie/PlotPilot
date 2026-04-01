/**
 * 子项目 8：工作流 / 长任务 / 一致性 / 故事线
 * 后端路由实现见 `docs/superpowers/plans/2026-04-02-subproject-8-frontend-extensions.md`
 */
import { apiClient } from './config'
import type { JobCreateResponse, JobStatusResponse } from '../types/api'

export interface GenerateChapterWithContextPayload {
  chapter_number: number
  outline: string
}

/** 与 `interfaces/api/v1/generation.py` GenerateChapterResponse 对齐 */
export interface ConsistencyIssueDTO {
  type: string
  severity: string
  description: string
  location: number
}

export interface ConsistencyReportDTO {
  issues: ConsistencyIssueDTO[]
  warnings: ConsistencyIssueDTO[]
  suggestions: string[]
}

export interface GenerateChapterWorkflowResponse {
  content: string
  consistency_report: ConsistencyReportDTO
  token_count: number
}

export type GenerateChapterStreamEvent =
  | { type: 'phase'; phase: 'planning' | 'context' | 'llm' | 'post' }
  | { type: 'chunk'; text: string }
  | { type: 'done'; content: string; consistency_report: ConsistencyReportDTO; token_count: number }
  | { type: 'error'; message: string }

function parseSseDataLine(line: string): unknown | null {
  if (!line.startsWith('data: ')) return null
  try {
    return JSON.parse(line.slice(6)) as unknown
  } catch {
    return null
  }
}

/**
 * POST /api/v1/novels/{novel_id}/generate-chapter-stream（SSE）
 * 阶段进度 + 正文流式；结束事件含 done 或 error。
 */
export async function consumeGenerateChapterStream(
  novelId: string,
  data: GenerateChapterWithContextPayload,
  handlers: {
    onEvent?: (ev: GenerateChapterStreamEvent) => void
    onPhase?: (phase: string) => void
    onChunk?: (text: string) => void
    onDone?: (result: GenerateChapterWorkflowResponse) => void
    onError?: (message: string) => void
    signal?: AbortSignal
  }
): Promise<void> {
  const res = await fetch(`/api/v1/novels/${novelId}/generate-chapter-stream`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
    signal: handlers.signal,
  })
  if (!res.ok || !res.body) {
    const t = await res.text().catch(() => '')
    handlers.onError?.(t || `HTTP ${res.status}`)
    return
  }
  const reader = res.body.getReader()
  const dec = new TextDecoder()
  let buf = ''
  try {
    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      buf += dec.decode(value, { stream: true })
      let sep: number
      while ((sep = buf.indexOf('\n\n')) >= 0) {
        const block = buf.slice(0, sep)
        buf = buf.slice(sep + 2)
        for (const line of block.split('\n')) {
          const raw = parseSseDataLine(line)
          if (!raw || typeof raw !== 'object' || raw === null) continue
          const o = raw as Record<string, unknown>
          const typ = o.type as string
          if (typ === 'phase') {
            const ph = String(o.phase ?? '')
            const ev: GenerateChapterStreamEvent = { type: 'phase', phase: ph as 'planning' | 'context' | 'llm' | 'post' }
            handlers.onEvent?.(ev)
            handlers.onPhase?.(ph)
          } else if (typ === 'chunk') {
            const text = String(o.text ?? '')
            const ev: GenerateChapterStreamEvent = { type: 'chunk', text }
            handlers.onEvent?.(ev)
            handlers.onChunk?.(text)
          } else if (typ === 'done') {
            const result: GenerateChapterWorkflowResponse = {
              content: String(o.content ?? ''),
              consistency_report: o.consistency_report as ConsistencyReportDTO,
              token_count: Number(o.token_count ?? 0),
            }
            const ev: GenerateChapterStreamEvent = { type: 'done', ...result }
            handlers.onEvent?.(ev)
            handlers.onDone?.(result)
            return
          } else if (typ === 'error') {
            const msg = String(o.message ?? '生成失败')
            const ev: GenerateChapterStreamEvent = { type: 'error', message: msg }
            handlers.onEvent?.(ev)
            handlers.onError?.(msg)
            return
          }
        }
      }
    }
  } catch (e: unknown) {
    if (e instanceof Error && e.name === 'AbortError') return
    const msg = e instanceof Error ? e.message : '流式连接失败'
    handlers.onError?.(msg)
  }
}

export interface HostedWritePayload {
  from_chapter: number
  to_chapter: number
  auto_save: boolean
  auto_outline: boolean
}

/**
 * POST /api/v1/novels/{novel_id}/hosted-write-stream — 托管多章连写（SSE，每行 JSON）
 */
export async function consumeHostedWriteStream(
  novelId: string,
  body: HostedWritePayload,
  handlers: {
    onEvent?: (o: Record<string, unknown>) => void
    onError?: (message: string) => void
    signal?: AbortSignal
  }
): Promise<void> {
  const res = await fetch(`/api/v1/novels/${novelId}/hosted-write-stream`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
    signal: handlers.signal,
  })
  if (!res.ok || !res.body) {
    const t = await res.text().catch(() => '')
    handlers.onError?.(t || `HTTP ${res.status}`)
    return
  }
  const reader = res.body.getReader()
  const dec = new TextDecoder()
  let buf = ''
  try {
    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      buf += dec.decode(value, { stream: true })
      let sep: number
      while ((sep = buf.indexOf('\n\n')) >= 0) {
        const block = buf.slice(0, sep)
        buf = buf.slice(sep + 2)
        for (const line of block.split('\n')) {
          const raw = parseSseDataLine(line)
          if (!raw || typeof raw !== 'object' || raw === null) continue
          const o = raw as Record<string, unknown>
          handlers.onEvent?.(o)
          if (o.type === 'error') {
            handlers.onError?.(String(o.message ?? 'error'))
            return
          }
        }
      }
    }
  } catch (e: unknown) {
    if (e instanceof Error && e.name === 'AbortError') return
    handlers.onError?.(e instanceof Error ? e.message : '流式连接失败')
  }
}

export const workflowApi = {
  /**
   * POST /api/v1/novels/{novel_id}/generate-chapter
   * AutoNovelGenerationWorkflow：上下文 + 生成 + 一致性报告（子项目 8）
   */
  generateChapterWithContext: (novelId: string, data: GenerateChapterWithContextPayload) =>
    apiClient.post<GenerateChapterWorkflowResponse>(
      `/novels/${novelId}/generate-chapter`,
      data,
      { timeout: 180_000 }
    ) as Promise<GenerateChapterWorkflowResponse>,

  /** GET /api/v1/novels/{novel_id}/consistency-report */
  getConsistencyReport: (novelId: string, chapter?: number) =>
    apiClient.get<unknown>(`/novels/${novelId}/consistency-report`, {
      params: chapter != null ? { chapter } : {},
    }) as Promise<unknown>,

  /** GET /api/v1/novels/{novel_id}/storylines */
  getStorylines: (novelId: string) =>
    apiClient.get<unknown>(`/novels/${novelId}/storylines`) as Promise<unknown>,

  /** POST /api/v1/novels/{novel_id}/plot-arc（body 含 key_points 等，见后端 CreatePlotArcRequest） */
  createPlotArc: (novelId: string, data: Record<string, unknown>) =>
    apiClient.post<unknown>(`/novels/${novelId}/plot-arc`, data) as Promise<unknown>,

  /**
   * 以下 Job 路由 **后端尚未实现**（`interfaces` 无 `/jobs`），调用会 404。
   * 单章/流式：`generateChapterWithContext` / `consumeGenerateChapterStream`；
   * 多章托管：`consumeHostedWriteStream`（`/hosted-write-stream`）。
   */
  /** POST /api/v1/novels/{novel_id}/jobs/plan */
  startPlanJob: (novelId: string, dryRun = false, mode: 'initial' | 'revise' = 'initial') =>
    apiClient.post<JobCreateResponse>(`/novels/${novelId}/jobs/plan`, {
      dry_run: dryRun,
      mode,
    }) as Promise<JobCreateResponse>,

  /** POST /api/v1/novels/{novel_id}/jobs/write */
  startWriteJob: (
    novelId: string,
    from: number,
    to?: number,
    dryRun = false,
    continuity = false
  ) =>
    apiClient.post<JobCreateResponse>(`/novels/${novelId}/jobs/write`, {
      from_chapter: from,
      to_chapter: to,
      dry_run: dryRun,
      continuity,
    }) as Promise<JobCreateResponse>,

  /** POST /api/v1/novels/{novel_id}/jobs/run */
  startRunJob: (novelId: string, dryRun = false, continuity = false) =>
    apiClient.post<JobCreateResponse>(`/novels/${novelId}/jobs/run`, {
      dry_run: dryRun,
      continuity,
    }) as Promise<JobCreateResponse>,

  /** POST /api/v1/novels/{novel_id}/jobs/export */
  exportBook: (novelId: string) =>
    apiClient.post<unknown>(`/novels/${novelId}/jobs/export`, {}) as Promise<unknown>,

  /** GET /api/v1/jobs/{job_id} */
  getJobStatus: (jobId: string) =>
    apiClient.get<JobStatusResponse>(`/jobs/${jobId}`) as Promise<JobStatusResponse>,

  /** POST /api/v1/jobs/{job_id}/cancel */
  cancelJob: (jobId: string) =>
    apiClient.post<{ ok: boolean }>(`/jobs/${jobId}/cancel`, {}) as Promise<{ ok: boolean }>,
}
