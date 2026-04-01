<template>
  <n-modal
    v-model:show="show"
    preset="card"
    style="width: min(820px, 98vw)"
    :mask-closable="false"
    :segmented="{ content: true, footer: 'soft' }"
    title="完整工作流撰稿"
  >
    <template #header-extra>
      <n-text depth="3" style="font-size: 12px">上下文 + 流式 + 一致性 · 单章 / 托管连写</n-text>
    </template>

    <n-tabs v-model:value="mainTab" type="line" size="small" class="gwm-tabs">
      <n-tab-pane name="single" tab="单章撰稿">
        <n-space vertical :size="14" class="gwm-body">
          <n-alert v-if="!result" type="info" :show-icon="true" class="gwm-intro">
            与侧栏「对话」互补：对话负责多轮讨论与工具编排；此处按大纲生成整章、流式展示、一致性校验后保存到章节。
          </n-alert>
          <n-form-item label="章节" :show-feedback="false">
            <n-select
              v-model:value="chapterNumber"
              :options="chapterOptions"
              placeholder="选择章号"
              :disabled="generating"
            />
          </n-form-item>
          <n-form-item label="本章大纲" :show-feedback="false">
            <n-input
              v-model:value="outline"
              type="textarea"
              placeholder="粘贴或编写本章大纲（必填）"
              :autosize="{ minRows: 5, maxRows: 14 }"
              :disabled="generating"
            />
          </n-form-item>

          <n-form-item v-if="!result" label="生成方式" :show-feedback="false">
            <n-space align="center" :size="12">
              <n-switch v-model:value="useStream" :disabled="generating" />
              <n-text depth="3">流式（实时阶段 + 正文逐段显示，推荐）</n-text>
            </n-space>
          </n-form-item>

          <template v-if="!result && generating && useStream">
            <n-space vertical :size="10">
              <n-progress
                type="line"
                :percentage="streamProgress"
                :processing="streamProgress < 100"
                :height="10"
                indicator-placement="inside"
              />
              <n-text depth="3">{{ phaseLabel }}</n-text>
              <n-input
                v-model:value="editedContent"
                type="textarea"
                placeholder="正文将在此流式出现…"
                :autosize="{ minRows: 8, maxRows: 22 }"
                readonly
              />
              <n-button size="small" secondary @click="stopStream">停止生成</n-button>
            </n-space>
          </template>

          <n-space v-if="!result" justify="end" :size="10">
            <n-button @click="close">取消</n-button>
            <n-button type="primary" :loading="generating" :disabled="generating" @click="runGenerate">生成</n-button>
          </n-space>

          <template v-else>
            <n-alert v-if="saveError" type="error" :title="saveError" />
            <ConsistencyReportPanel
              :report="result.consistency_report"
              :token-count="result.token_count"
              @location-click="onLocationClick"
            />
            <n-form-item label="正文（可编辑后再保存）" :show-feedback="false">
              <n-input
                v-model:value="editedContent"
                type="textarea"
                :autosize="{ minRows: 12, maxRows: 28 }"
                :disabled="saving"
              />
            </n-form-item>
            <n-space justify="end" :size="10">
              <n-button @click="resetResult">重新生成</n-button>
              <n-button type="primary" :loading="saving" @click="saveToChapter">保存到章节</n-button>
            </n-space>
          </template>
        </n-space>
      </n-tab-pane>

      <n-tab-pane name="hosted" tab="托管连写">
        <n-space vertical :size="14" class="gwm-body">
          <n-alert type="warning" :show-icon="true" class="gwm-intro">
            全自动区间：每章先用模型生成要点大纲（可关则用语义模板），再按章流式正文；上下文由后端
            ContextBuilder 维护。请确保章号已在书中存在，否则无法自动保存。
          </n-alert>
          <n-form-item label="章区间（含端点）" :show-feedback="false">
            <n-space align="center" :size="12" wrap>
              <n-input-number
                v-model:value="hostedFrom"
                :min="1"
                :disabled="hostedRunning"
                placeholder="起"
              />
              <span>—</span>
              <n-input-number
                v-model:value="hostedTo"
                :min="1"
                :disabled="hostedRunning"
                placeholder="止"
              />
            </n-space>
          </n-form-item>
          <n-form-item :show-feedback="false">
            <n-space vertical :size="8">
              <n-space align="center" :size="12">
                <n-switch v-model:value="hostedAutoOutline" :disabled="hostedRunning" />
                <n-text depth="3">自动大纲（LLM 要点，推荐）</n-text>
              </n-space>
              <n-space align="center" :size="12">
                <n-switch v-model:value="hostedAutoSave" :disabled="hostedRunning" />
                <n-text depth="3">每章生成后写入章节正文</n-text>
              </n-space>
            </n-space>
          </n-form-item>

          <n-text depth="3">当前章正文预览</n-text>
          <n-input
            v-model:value="hostedPreview"
            type="textarea"
            readonly
            placeholder="托管运行中，本章流式正文会出现在此…"
            :autosize="{ minRows: 6, maxRows: 16 }"
          />
          <n-text depth="3">事件日志</n-text>
          <n-input v-model:value="hostedLog" type="textarea" readonly :autosize="{ minRows: 6, maxRows: 12 }" />

          <n-space justify="end" :size="10" wrap>
            <n-button @click="close" :disabled="hostedRunning">关闭</n-button>
            <n-button secondary :disabled="!hostedRunning" @click="stopHosted">停止</n-button>
            <n-button type="primary" :loading="hostedRunning" :disabled="hostedRunning" @click="runHosted">
              开始托管
            </n-button>
          </n-space>
        </n-space>
      </n-tab-pane>
    </n-tabs>
  </n-modal>
</template>

<script setup lang="ts">
import { ref, watch, computed } from 'vue'
import { useMessage } from 'naive-ui'
import {
  workflowApi,
  consumeGenerateChapterStream,
  consumeHostedWriteStream,
  type GenerateChapterWorkflowResponse,
} from '../../api/workflow'
import { chapterApi } from '../../api/chapter'
import ConsistencyReportPanel from './ConsistencyReportPanel.vue'

export interface ChapterOption {
  id: number
  title: string
}

const props = defineProps<{
  show: boolean
  slug: string
  chapters: ChapterOption[]
  defaultChapterId?: number | null
}>()

const emit = defineEmits<{
  (e: 'update:show', v: boolean): void
  (e: 'saved'): void
}>()

const message = useMessage()

const show = computed({
  get: () => props.show,
  set: (v: boolean) => emit('update:show', v),
})

const mainTab = ref<'single' | 'hosted'>('single')

const chapterNumber = ref<number | null>(null)
const outline = ref('')
const generating = ref(false)
const saving = ref(false)
const saveError = ref('')
const result = ref<GenerateChapterWorkflowResponse | null>(null)
const editedContent = ref('')
const useStream = ref(true)
const streamProgress = ref(0)
const phaseLabel = ref('')
let streamAbort: AbortController | null = null
let chunkCount = 0

const hostedFrom = ref<number | null>(1)
const hostedTo = ref<number | null>(1)
const hostedAutoOutline = ref(true)
const hostedAutoSave = ref(true)
const hostedRunning = ref(false)
const hostedLog = ref('')
const hostedPreview = ref('')
let hostedAbort: AbortController | null = null

const chapterOptions = computed(() =>
  props.chapters.map(c => ({
    label: `第${c.id}章 ${c.title ? c.title.slice(0, 16) : ''}`,
    value: c.id,
  }))
)

watch(
  () => [props.show, props.chapters, props.defaultChapterId] as const,
  () => {
    if (!props.show) return
    const ch = props.chapters
    if (!ch.length) {
      chapterNumber.value = null
      hostedFrom.value = 1
      hostedTo.value = 1
      return
    }
    const def = props.defaultChapterId
    if (def != null && ch.some(x => x.id === def)) {
      chapterNumber.value = def
    } else if (chapterNumber.value == null || !ch.some(x => x.id === chapterNumber.value)) {
      chapterNumber.value = ch[0].id
    }
    const ids = ch.map(c => c.id).sort((a, b) => a - b)
    hostedFrom.value = ids[0]
    hostedTo.value = ids[ids.length - 1]
  },
  { immediate: true }
)

watch(
  () => props.show,
  v => {
    if (!v) {
      generating.value = false
      saveError.value = ''
      streamAbort?.abort()
      streamAbort = null
      result.value = null
      editedContent.value = ''
      outline.value = ''
      streamProgress.value = 0
      phaseLabel.value = ''
      mainTab.value = 'single'
      hostedAbort?.abort()
      hostedAbort = null
      hostedRunning.value = false
      hostedLog.value = ''
      hostedPreview.value = ''
    }
  }
)

function close() {
  streamAbort?.abort()
  hostedAbort?.abort()
  emit('update:show', false)
}

function resetResult() {
  result.value = null
  editedContent.value = ''
  saveError.value = ''
  streamProgress.value = 0
  phaseLabel.value = ''
}

function phaseToProgress(phase: string): number {
  const map: Record<string, number> = {
    planning: 12,
    context: 28,
    llm: 38,
    post: 92,
  }
  return map[phase] ?? streamProgress.value
}

function stopStream() {
  streamAbort?.abort()
  streamAbort = null
  generating.value = false
  phaseLabel.value = '已停止'
}

function stopHosted() {
  hostedAbort?.abort()
  hostedAbort = null
  hostedRunning.value = false
  message.info('已请求停止（当前章结束后不再续写）')
}

function appendHostedLog(line: string) {
  const next = (hostedLog.value + line + '\n').slice(-12000)
  hostedLog.value = next
}

async function runHosted() {
  const a = hostedFrom.value
  const b = hostedTo.value
  if (a == null || b == null) {
    message.warning('请填写章区间')
    return
  }
  if (b < a) {
    message.warning('结束章不能小于起始章')
    return
  }
  hostedRunning.value = true
  hostedLog.value = ''
  hostedPreview.value = ''
  hostedAbort = new AbortController()
  let currentChapter: number | null = null

  await consumeHostedWriteStream(
    props.slug,
    {
      from_chapter: a,
      to_chapter: b,
      auto_save: hostedAutoSave.value,
      auto_outline: hostedAutoOutline.value,
    },
    {
      signal: hostedAbort.signal,
      onEvent: o => {
        appendHostedLog(JSON.stringify(o))
        const t = o.type as string
        if (t === 'chapter_start') {
          currentChapter = Number(o.chapter ?? 0)
          hostedPreview.value = ''
        }
        if (t === 'chunk' && o.chapter != null) {
          if (currentChapter !== Number(o.chapter)) {
            currentChapter = Number(o.chapter)
            hostedPreview.value = ''
          }
          hostedPreview.value += String(o.text ?? '')
        }
        if (t === 'session_done') {
          message.success('托管区间已完成')
          emit('saved')
        }
      },
      onError: msg => {
        message.error(msg || '托管失败')
      },
    }
  )
  hostedAbort = null
  hostedRunning.value = false
}

async function runGenerate() {
  const n = chapterNumber.value
  const o = outline.value.trim()
  if (n == null) {
    message.warning('请选择章节')
    return
  }
  if (!o) {
    message.warning('请填写本章大纲')
    return
  }
  generating.value = true
  saveError.value = ''
  editedContent.value = ''
  streamProgress.value = 4
  phaseLabel.value = '准备中…'
  chunkCount = 0

  if (useStream.value) {
    streamAbort = new AbortController()
    await consumeGenerateChapterStream(
      props.slug,
      { chapter_number: n, outline: o },
      {
        signal: streamAbort.signal,
        onPhase: phase => {
          streamProgress.value = phaseToProgress(phase)
          const labels: Record<string, string> = {
            planning: '叙事与故事线规划…',
            context: '构建上下文（圣经 / 摘要等）…',
            llm: '模型正在生成本章正文…',
            post: '一致性检查与收尾…',
          }
          phaseLabel.value = labels[phase] ?? phase
        },
        onChunk: text => {
          chunkCount += 1
          editedContent.value += text
          streamProgress.value = Math.min(88, 38 + Math.min(chunkCount * 0.35, 50))
        },
        onDone: data => {
          result.value = data
          editedContent.value = data.content || ''
          streamProgress.value = 100
          phaseLabel.value = '完成'
          message.success('生成完成')
        },
        onError: msg => {
          message.error(msg || '生成失败')
        },
      }
    )
    streamAbort = null
    generating.value = false
    if (result.value) return
    return
  }

  try {
    const data = await workflowApi.generateChapterWithContext(props.slug, {
      chapter_number: n,
      outline: o,
    })
    result.value = data
    editedContent.value = data.content || ''
    message.success('生成完成')
  } catch (e: unknown) {
    const err = e as { response?: { data?: { detail?: string } }; message?: string }
    message.error(err.response?.data?.detail || err.message || '生成失败')
  } finally {
    generating.value = false
  }
}

async function saveToChapter() {
  const n = chapterNumber.value
  if (n == null) return
  const content = editedContent.value
  saving.value = true
  saveError.value = ''
  try {
    await chapterApi.updateChapter(props.slug, n, { content })
    message.success('已保存到章节')
    emit('saved')
    emit('update:show', false)
    result.value = null
    editedContent.value = ''
    outline.value = ''
  } catch (e: unknown) {
    const err = e as { response?: { data?: { detail?: string } }; message?: string }
    saveError.value = err.response?.data?.detail || err.message || '保存失败'
  } finally {
    saving.value = false
  }
}

function onLocationClick(location: number) {
  message.info(`问题位置标记：${location}（可在章节视图内对照）`)
}
</script>

<style scoped>
.gwm-body {
  width: 100%;
}
.gwm-intro {
  font-size: 13px;
}
.gwm-tabs :deep(.n-tabs-nav) {
  margin-bottom: 8px;
}
</style>
