<template>
  <div class="chat-area">
    <header class="chat-header">
      <div class="chat-title-wrap">
        <h2 class="chat-title">{{ bookTitle || slug }}</h2>
        <n-text depth="3" class="chat-sub">{{ slug }}</n-text>
      </div>
      <n-space :size="12" align="center" wrap class="chat-header-actions">
        <n-button-group size="small">
          <n-button :type="rightPanel === 'bible' ? 'primary' : 'default'" @click="setRightPanel('bible')">
            设定
          </n-button>
          <n-button :type="rightPanel === 'knowledge' ? 'primary' : 'default'" @click="setRightPanel('knowledge')">
            叙事与关系
          </n-button>
        </n-button-group>
        <n-divider vertical style="height: 22px; margin: 0" />
        <n-space :size="8" align="center" wrap>
          <n-button size="small" secondary @click="openPlanModal">结构规划</n-button>
          <n-tooltip trigger="hover">
            <template #trigger>
              <n-button size="small" type="primary" @click="startWrite">撰稿</n-button>
            </template>
            单章 / 托管连写：自动大纲、多章流式、上下文由后端维护。下方对话区仍用于多轮讨论与工具调用。
          </n-tooltip>
        </n-space>
      </n-space>
    </header>

    <n-scrollbar ref="messageScrollRef" class="chat-messages">
      <div class="chat-messages-pad">
        <div
          v-for="msg in messages"
          :key="msg.id"
          class="msg-row"
          :class="msg.role"
        >
          <div class="msg-bubble">
            <div class="msg-meta">
              <n-tag size="small" round :type="getRoleType(msg.role)">
                {{ getRoleLabel(msg.role, msg.meta) }}
              </n-tag>
              <span class="msg-time">{{ formatTime(msg.ts) }}</span>
            </div>
            <div
              v-if="msg.role === 'assistant' && msg.meta?.tools?.length"
              class="msg-tools"
            >
              <span class="msg-tools-title">工具调用</span>
              <div
                v-for="(t, ti) in msg.meta.tools"
                :key="ti"
                class="msg-tool-line"
              >
                <n-tag size="tiny" round :type="t.ok ? 'success' : 'error'" :bordered="false">
                  {{ t.name }}
                </n-tag>
                <span class="msg-tool-detail">{{ t.detail }}</span>
              </div>
            </div>
            <div class="markdown-body md-body msg-md" v-html="renderMarkdown(msg.content)" />
          </div>
        </div>

        <div v-if="streamActive" class="msg-row assistant stream-live">
          <div class="msg-bubble stream-live-bubble">
            <div class="msg-meta">
              <n-tag size="small" round type="info">助手 · 生成中</n-tag>
            </div>
            <div v-if="streamTools.length" class="msg-tools stream-thinking">
              <span class="msg-tools-title">工具步骤（实时）</span>
              <div
                v-for="(t, ti) in streamTools"
                :key="ti"
                class="msg-tool-line"
              >
                <n-tag size="tiny" round :type="t.ok ? 'success' : 'error'" :bordered="false">
                  {{ t.name }}
                </n-tag>
                <span class="msg-tool-detail">{{ t.detail }}</span>
              </div>
            </div>
            <div
              class="markdown-body md-body msg-md stream-md"
              v-html="renderMarkdown(streamText)"
            />
          </div>
        </div>
      </div>
    </n-scrollbar>

    <div class="composer">
      <div class="composer-toolbar">
        <n-radio-group v-model:value="historyMode" size="small">
          <n-radio-button value="full">带历史</n-radio-button>
          <n-radio-button value="fresh">仅本轮</n-radio-button>
        </n-radio-group>
        <n-space :size="6" align="center" wrap>
          <n-select
            v-model:value="chapterPick"
            size="tiny"
            class="ch-pick-select"
            :options="chapterSelectOptions"
            placeholder="章"
          />
          <n-checkbox v-model:checked="clearBeforeSend" size="small" class="clear-before-check">
            本条发送前清空对话
          </n-checkbox>
          <n-checkbox v-model:checked="useStreamMode" size="small">流式输出</n-checkbox>
          <n-checkbox v-model:checked="useStreamDraft" size="small">流式撰稿区</n-checkbox>
          <n-dropdown trigger="click" :options="clearMenuOptions" @select="onClearMenu">
            <n-button size="tiny" quaternary>清空上下文</n-button>
          </n-dropdown>
        </n-space>
      </div>
      <n-space :size="6" wrap class="quick-prompts">
        <n-button size="tiny" tertiary @click="fillQuick('chapter')">本章撰稿</n-button>
        <n-button size="tiny" tertiary @click="fillQuick('batch')">批量章摘要</n-button>
        <n-button size="tiny" tertiary @click="fillQuick('check')">梗概对齐检查</n-button>
      </n-space>
      <n-text depth="3" class="aitext-composer-hint">
        {{
          historyMode === 'fresh'
            ? '仅本轮：不带此前多轮对话，仍含全书设定/梗概/叙事注入。Enter 发送；Ctrl+Enter 换行；Shift+Enter 换行。'
            : '带历史：多轮对话参与上下文。开启「流式输出」时工具步骤会像思考过程一样逐条出现，正文分块显示；可开「流式撰稿区」同步到大编辑框。Enter 发送；Ctrl+Enter 换行；Shift+Enter 换行。'
        }}
        默认已开启流式输出。需要按大纲整章成稿并写入章节时，请用右上角「撰稿」。
      </n-text>
      <n-input
        v-model:value="inputMessage"
        type="textarea"
        :rows="3"
        placeholder="输入编务指令，或点上方快捷话术…"
        :disabled="sending"
        class="composer-input"
        @keydown.enter="onComposerKeydown"
      />
      <div class="composer-actions">
        <n-button v-if="!sending" type="primary" round @click="sendMessage">发送</n-button>
        <n-button v-else type="primary" loading round disabled>生成中…</n-button>
      </div>
    </div>

    <n-drawer
      v-model:show="streamDraftVisible"
      :height="420"
      placement="bottom"
      :trap-focus="false"
      :auto-focus="false"
    >
      <n-drawer-content title="流式撰稿区（正文同步，可编辑）" closable>
        <n-input
          v-model:value="streamText"
          type="textarea"
          placeholder="生成中正文会追加到此；可边生成边改。"
          :autosize="{ minRows: 14, maxRows: 28 }"
          class="stream-draft-input"
        />
      </n-drawer-content>
    </n-drawer>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, onMounted, onUnmounted, nextTick, computed } from 'vue'
import { useMessage } from 'naive-ui'
import { chatApi } from '../../api/chat'
import { marked } from 'marked'
import DOMPurify from 'dompurify'
import type { ChapterListItem, ChatMessage } from '../../types/api'

interface Props {
  slug: string
  bookTitle: string
  chapters: ChapterListItem[]
  currentChapterId?: number | null
}

const props = withDefaults(defineProps<Props>(), {
  currentChapterId: null
})

interface Emits {
  (e: 'set-right-panel', panel: 'bible' | 'knowledge'): void
  (e: 'open-plan-modal'): void
  (e: 'start-write'): void
  (e: 'messages-updated'): void
}

const emit = defineEmits<Emits>()

const message = useMessage()

// Chat state
const messages = ref<ChatMessage[]>([])
const inputMessage = ref('')
const sending = ref(false)
/** 对话上下文：full 带多轮；fresh 仅本轮用户句 + 全书 system */
const historyMode = ref<'full' | 'fresh'>('full')
const chapterPick = ref<number | null>(null)
/** 与「清空上下文」下拉不同：仅本条 user 写入前清空 thread */
const clearBeforeSend = ref(false)
/** 开启时用 SSE：工具步骤实时展示 + 正文分块；关闭时用原有一轮非流式请求 */
const useStreamMode = ref(true)
/** 生成开始时若勾选则自动打开底部抽屉，与 streamText 双向同步便于边生成边改 */
const useStreamDraft = ref(false)
const streamDraftVisible = ref(false)
const streamActive = ref(false)
const streamText = ref('')
const streamTools = ref<Array<{ name: string; ok: boolean; detail: string }>>([])
const rightPanel = ref<'bible' | 'knowledge'>('knowledge')

interface ScrollToParams {
  top: number
  behavior: ScrollBehavior
}

const messageScrollRef = ref<{ scrollTo: (params: ScrollToParams) => void } | null>(null)

// AbortController for SSE stream cleanup
let abortController: AbortController | null = null

// Scroll performance optimization with requestAnimationFrame
let scrollRaf: number | null = null

const chapterSelectOptions = computed(() =>
  props.chapters.map(c => ({ label: `第${c.id}章 ${c.title ? c.title.slice(0, 8) : ''}`, value: c.id }))
)

const clearMenuOptions = [
  { label: '仅清空对话', key: 'thread' },
  { label: '对话 + 远期摘要', key: 'both' },
]

watch(
  () => props.chapters,
  ch => {
    if (!ch?.length) {
      chapterPick.value = null
      return
    }
    if (chapterPick.value == null || !ch.some((x: ChapterListItem) => x.id === chapterPick.value)) {
      chapterPick.value = ch[0].id
    }
  },
  { immediate: true }
)

watch(() => props.currentChapterId, id => {
  if (id != null && !Number.isNaN(id)) chapterPick.value = id
})

watch([streamText, streamTools], () => {
  if (streamActive.value) scrollToBottom()
})

const onClearMenu = async (key: string | number) => {
  const k = String(key)
  try {
    await chatApi.clearThread(props.slug, k === 'both')
    await fetchMessages()
    message.success(k === 'both' ? '已清空对话与远期摘要' : '已清空对话记录')
  } catch (error: Error | unknown) {
    const errorMessage = error instanceof Error ? error.message : '清空失败'
    message.error(errorMessage)
  }
}

const fillQuick = (kind: 'chapter' | 'batch' | 'check') => {
  const n = chapterPick.value ?? props.chapters[0]?.id ?? 1
  if (kind === 'chapter') {
    inputMessage.value = `请结合分章大纲与侧栏叙事，协助撰写第 ${n} 章：先给出节拍/子段落，再说明将调用的工具（如 story_upsert_chapter_summary）及字段；人物关系以 cast_* 为准。`
  } else if (kind === 'batch') {
    inputMessage.value =
      '请规划并调用工具，批量更新第 __ 章至第 __ 章的章摘要（story_upsert_chapter_summary），保持梗概锁定与关系图一致；先列章号计划再逐步执行。'
  } else {
    inputMessage.value =
      '请对照 manifest 与侧栏「梗概锁定」，检查当前叙事风险；必要时先 story_get_snapshot 再给出修订建议。'
  }
}

const setRightPanel = (p: 'bible' | 'knowledge') => {
  rightPanel.value = p
  emit('set-right-panel', p)
}

const fetchMessages = async () => {
  const res = await chatApi.getMessages(props.slug)
  messages.value = res.messages || []
  emit('messages-updated')
  await nextTick()
  scrollToBottom()
}

const scrollToBottom = () => {
  if (scrollRaf) cancelAnimationFrame(scrollRaf)
  scrollRaf = requestAnimationFrame(() => {
    messageScrollRef.value?.scrollTo({ top: 999999, behavior: 'smooth' })
  })
}

/** Enter 发送；Ctrl/Cmd+Enter 插入换行；Shift+Enter 保持默认换行 */
const onComposerKeydown = (e: KeyboardEvent) => {
  if (e.key !== 'Enter') return
  if (e.ctrlKey || e.metaKey) {
    e.preventDefault()
    const el = e.target as HTMLTextAreaElement
    const start = el.selectionStart ?? 0
    const end = el.selectionEnd ?? 0
    const v = inputMessage.value
    inputMessage.value = v.slice(0, start) + '\n' + v.slice(end)
    nextTick(() => {
      el.selectionStart = el.selectionEnd = start + 1
    })
    return
  }
  if (e.shiftKey) return
  e.preventDefault()
  void sendMessage()
}

const parseSseLine = (line: string): Record<string, unknown> | null => {
  if (!line.startsWith('data: ')) return null
  try {
    return JSON.parse(line.slice(6)) as Record<string, unknown>
  } catch {
    return null
  }
}

const sendMessageStream = async (userMessage: string, clearFlag: boolean) => {
  streamTools.value = []
  streamText.value = ''
  streamActive.value = true
  if (useStreamDraft.value) streamDraftVisible.value = true
  scrollToBottom()

  // Create new AbortController for this stream
  abortController = new AbortController()
  const controller = abortController

  let res: Response
  try {
    res = await chatApi.sendStream(props.slug, userMessage, {
      use_cast_tools: true,
      history_mode: historyMode.value,
      clear_thread: clearFlag,
    })
  } catch (error: Error | unknown) {
    if (controller.signal.aborted) return
    streamActive.value = false
    message.error('网络错误')
    return
  }

  clearBeforeSend.value = false
  if (!res.ok || !res.body) {
    streamActive.value = false
    const text = await res.text().catch(() => '')
    message.error(text || `请求失败 ${res.status}`)
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
          const json = parseSseLine(line)
          if (!json) continue
          const typ = json.type as string
          if (typ === 'tool') {
            streamTools.value = [
              ...streamTools.value,
              {
                name: String(json.name ?? ''),
                ok: !!json.ok,
                detail: String(json.detail ?? ''),
              },
            ]
          } else if (typ === 'chunk') {
            streamText.value += String(json.text ?? '')
          } else if (typ === 'done') {
            await fetchMessages()
            scrollToBottom()
          } else if (typ === 'error') {
            message.error(String(json.message ?? '生成失败'))
            await fetchMessages()
          }
        }
      }
    }
  } catch (error: Error | unknown) {
    // Check if this is an abort error from component unmount
    if (error instanceof Error && error.name === 'AbortError') return
    message.error(error instanceof Error ? error.message : '流式生成失败')
  } finally {
    streamActive.value = false
    streamText.value = ''
    streamTools.value = []
  }
}

const sendMessage = async () => {
  if (!inputMessage.value.trim() || sending.value) return

  const userMessage = inputMessage.value
  inputMessage.value = ''
  sending.value = true
  const clearFlag = clearBeforeSend.value
  try {
    if (useStreamMode.value) {
      await sendMessageStream(userMessage, clearFlag)
    } else {
      const res = await chatApi.send(props.slug, userMessage, {
        use_cast_tools: true,
        history_mode: historyMode.value,
        clear_thread: clearFlag,
      })
      clearBeforeSend.value = false
      if (res.ok) {
        await fetchMessages()
      } else {
        message.warning(res.reply || '未生成回复')
      }
    }
  } catch (error: Error | unknown) {
    const errorMessage = error instanceof Error ? error.message : '发送失败'
    message.error(errorMessage)
  } finally {
    sending.value = false
  }
}

// 侧栏知识检索「引用到输入框」
interface ComposerInsertEvent extends CustomEvent {
  detail: { text: string }
}

const onComposerInsert = (ev: Event) => {
  const customEvent = ev as ComposerInsertEvent
  const text = customEvent.detail?.text || ''
  if (!text.trim()) return
  if (!inputMessage.value.trim()) inputMessage.value = text
  else inputMessage.value = inputMessage.value.trimEnd() + '\n\n' + text
}

const openPlanModal = () => {
  emit('open-plan-modal')
}

const startWrite = () => {
  emit('start-write')
}

const getRoleLabel = (role: string, meta?: { tools?: unknown[] }) => {
  if (role === 'assistant' && meta?.tools?.length) return '助手 · 工具'
  const map: Record<string, string> = { user: '我', assistant: '助手', system: '系统' }
  return map[role] || role
}

const getRoleType = (role: string): 'info' | 'default' | 'warning' => {
  const map: Record<string, 'info' | 'default' | 'warning'> = {
    user: 'info',
    assistant: 'default',
    system: 'warning'
  }
  return map[role] || 'default'
}

const renderMarkdown = (content: string) => {
  const html = marked.parse(content || '', { breaks: true, async: false }) as string
  return DOMPurify.sanitize(html)
}

const formatTime = (ts: string) => {
  return new Date(ts).toLocaleString('zh-CN', { hour12: false })
}

onMounted(() => {
  window.addEventListener('aitext:composer:insert', onComposerInsert as EventListener)
  fetchMessages()
})

onUnmounted(() => {
  // Abort any ongoing stream to prevent memory leaks
  if (abortController) {
    abortController.abort()
  }

  // Clean up any pending scroll animation
  if (scrollRaf) {
    cancelAnimationFrame(scrollRaf)
  }

  window.removeEventListener('aitext:composer:insert', onComposerInsert as EventListener)
})

// Public methods that parent can call
defineExpose({
  fetchMessages,
  scrollToBottom
})
</script>

<style scoped>
.chat-area {
  height: 100%;
  min-height: 0;
  display: flex;
  flex-direction: column;
  background: var(--app-surface, #fff);
}

.chat-header {
  flex-shrink: 0;
  padding: 12px 16px;
  border-bottom: 1px solid var(--aitext-split-border);
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 12px;
  flex-wrap: wrap;
  background: rgba(255, 255, 255, 0.72);
  backdrop-filter: blur(10px);
}

.chat-header-actions {
  max-width: 100%;
}

.chat-title {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
  letter-spacing: -0.02em;
}

.chat-sub {
  display: block;
  margin-top: 6px;
  font-size: 12px;
  font-family: ui-monospace, monospace;
}

.chat-messages {
  flex: 1;
  min-height: 0;
}

.chat-messages-pad {
  padding: 16px 18px 24px;
  max-width: 900px;
  margin: 0 auto;
}

.msg-row {
  display: flex;
  margin-bottom: 14px;
  animation: msg-in 0.28s ease both;
}

@keyframes msg-in {
  from {
    opacity: 0;
    transform: translateY(8px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.msg-row.user {
  justify-content: flex-end;
}

.msg-row.assistant,
.msg-row.system {
  justify-content: flex-start;
}

.msg-bubble {
  max-width: min(92%, 720px);
  padding: 12px 14px;
  border-radius: 14px;
  box-shadow: var(--app-shadow);
}

.msg-row.user .msg-bubble {
  background: linear-gradient(135deg, #4f46e5 0%, #6366f1 100%);
  color: #fff;
}

.msg-row.user .msg-bubble .msg-time {
  color: rgba(255, 255, 255, 0.85);
}

.msg-row.assistant .msg-bubble,
.msg-row.system .msg-bubble {
  background: #f1f5f9;
  border: 1px solid var(--app-border);
}

.msg-meta {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 8px;
}

.msg-time {
  font-size: 12px;
  color: var(--n-text-color-3);
}

.msg-row.user :deep(.n-tag) {
  --n-color: rgba(255, 255, 255, 0.85);
  --n-text-color: #1e1b4b;
}

.msg-md {
  color: inherit;
}

.msg-row.user .msg-md :deep(a) {
  color: #e0e7ff;
}

.composer {
  flex-shrink: 0;
  padding: 12px 16px 16px;
  border-top: 1px solid var(--aitext-split-border);
  display: flex;
  flex-direction: column;
  gap: 8px;
  background: var(--app-surface);
}

.composer-input :deep(textarea) {
  font-size: 14px;
  line-height: 1.5;
}

.composer-actions {
  display: flex;
  justify-content: flex-end;
}

.composer-toolbar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  margin-bottom: 6px;
}

.ch-pick-select {
  min-width: 140px;
  max-width: 200px;
}

.clear-before-check {
  font-size: 12px;
}

.quick-prompts {
  margin-bottom: 6px;
}

.msg-tools {
  margin-bottom: 10px;
  padding: 8px 10px;
  border-radius: 10px;
  background: rgba(79, 70, 229, 0.06);
  border: 1px solid rgba(99, 102, 241, 0.18);
}

.msg-tools-title {
  display: block;
  font-size: 11px;
  font-weight: 600;
  color: #6366f1;
  margin-bottom: 6px;
  letter-spacing: 0.04em;
}

.msg-tool-line {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  margin-bottom: 4px;
  font-size: 12px;
}

.msg-tool-line:last-child {
  margin-bottom: 0;
}

.msg-tool-detail {
  color: #475569;
  line-height: 1.45;
  flex: 1;
  min-width: 0;
}

.stream-live .stream-live-bubble {
  border: 1px dashed rgba(99, 102, 241, 0.45);
  background: linear-gradient(180deg, #fafbff 0%, #f1f5f9 100%);
}

.stream-thinking {
  background: rgba(79, 70, 229, 0.07);
}

.stream-md {
  min-height: 1.25em;
}

.stream-draft-input :deep(textarea) {
  font-size: 14px;
  line-height: 1.55;
  font-family: ui-monospace, 'Cascadia Code', 'Segoe UI Mono', monospace;
}
</style>
