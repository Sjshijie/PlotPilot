<template>
  <div class="ce-panel">
    <n-empty v-if="!currentChapterNumber" description="请先从左侧选择一个章节" style="margin-top: 40px" />

    <template v-else>
      <n-scrollbar class="ce-scroll">
        <n-space vertical :size="12" style="padding-bottom: 16px">
          <n-alert v-if="readOnly" type="warning" :show-icon="true" style="font-size: 12px">
            托管运行中：仅可查看，不可增删元素关联。
          </n-alert>

          <!-- 本章规划（结构树节点：节拍/大纲/视角等） -->
          <n-card v-if="chapterPlan" title="本章规划（结构树）" size="small" :bordered="true">
            <n-space vertical :size="8">
              <n-text depth="3" style="font-size: 12px">
                与左侧「宏观规划」结构树同源；用于写作前对齐本章节拍与要点。
              </n-text>
              <n-descriptions :column="1" label-placement="left" size="small" label-style="white-space: nowrap">
                <n-descriptions-item label="标题">{{ chapterPlan.title || '—' }}</n-descriptions-item>
                <n-descriptions-item v-if="chapterPlan.outline" label="大纲 / 节拍">
                  <n-text style="font-size: 12px; white-space: pre-wrap">{{ chapterPlan.outline }}</n-text>
                </n-descriptions-item>
                <n-descriptions-item v-if="chapterPlan.description" label="摘要">
                  <n-text style="font-size: 12px; white-space: pre-wrap">{{ chapterPlan.description }}</n-text>
                </n-descriptions-item>
                <n-descriptions-item v-if="chapterPlan.pov_character_id" label="视角 POV">
                  {{ chapterPlan.pov_character_id }}
                </n-descriptions-item>
                <n-descriptions-item
                  v-if="chapterPlan.timeline_start || chapterPlan.timeline_end"
                  label="时间线"
                >
                  {{ chapterPlan.timeline_start || '—' }} → {{ chapterPlan.timeline_end || '—' }}
                </n-descriptions-item>
                <n-descriptions-item v-if="planMoodLine" label="情绪 / 基调">
                  {{ planMoodLine }}
                </n-descriptions-item>
              </n-descriptions>
            </n-space>
          </n-card>

          <n-alert v-else-if="storyNodeNotFound" type="warning" :show-icon="true">
            未在结构树中找到第 {{ currentChapterNumber }} 章的规划节点。请先在左侧「宏观规划」中创建章节结构；创建后此处将显示本章大纲、视角等，并支持下方元素关联。
          </n-alert>

          <!-- 元素关联 -->
          <n-card title="人物 / 地点 / 道具…（章级关联）" size="small" :bordered="true">
            <template #header-extra>
              <n-space :size="6">
                <n-select
                  v-model:value="filterType"
                  :options="elementTypeOptions"
                  size="tiny"
                  style="width: 90px"
                  clearable
                  placeholder="类型"
                  @update:value="loadElements"
                />
                <n-button size="tiny" secondary :loading="loading" @click="loadElements">刷新</n-button>
              </n-space>
            </template>

            <n-spin :show="loading">
              <n-space vertical :size="5">
                <n-space v-if="groupedCharacters.length" vertical :size="4">
                  <n-text strong style="font-size: 12px">人物</n-text>
                  <div v-for="elem in groupedCharacters" :key="elem.id" class="ce-item">
                    <div class="ce-item-info">
                      <n-tag :type="elemTypeColor(elem.element_type)" size="tiny" round>{{ elemTypeLabel(elem.element_type) }}</n-tag>
                      <n-text style="font-size:12px; flex:1">{{ elem.element_id }}</n-text>
                      <n-tag size="tiny" round>{{ elem.relation_type }}</n-tag>
                      <n-tag :type="elem.importance === 'major' ? 'error' : elem.importance === 'minor' ? 'default' : 'info'" size="tiny" round>
                        {{ importanceLabel(elem.importance) }}
                      </n-tag>
                    </div>
                    <n-button
                      v-if="!readOnly"
                      size="tiny"
                      type="error"
                      text
                      :loading="deletingId === elem.id"
                      @click="doDelete(elem)"
                    >删除</n-button>
                  </div>
                </n-space>

                <n-space v-if="groupedLocations.length" vertical :size="4">
                  <n-text strong style="font-size: 12px">地点</n-text>
                  <div v-for="elem in groupedLocations" :key="elem.id" class="ce-item">
                    <div class="ce-item-info">
                      <n-tag :type="elemTypeColor(elem.element_type)" size="tiny" round>{{ elemTypeLabel(elem.element_type) }}</n-tag>
                      <n-text style="font-size:12px; flex:1">{{ elem.element_id }}</n-text>
                      <n-tag size="tiny" round>{{ elem.relation_type }}</n-tag>
                      <n-tag :type="elem.importance === 'major' ? 'error' : elem.importance === 'minor' ? 'default' : 'info'" size="tiny" round>
                        {{ importanceLabel(elem.importance) }}
                      </n-tag>
                    </div>
                    <n-button
                      v-if="!readOnly"
                      size="tiny"
                      type="error"
                      text
                      :loading="deletingId === elem.id"
                      @click="doDelete(elem)"
                    >删除</n-button>
                  </div>
                </n-space>

                <n-space v-if="groupedOther.length" vertical :size="4">
                  <n-text strong style="font-size: 12px">其他</n-text>
                  <div v-for="elem in groupedOther" :key="elem.id" class="ce-item">
                    <div class="ce-item-info">
                      <n-tag :type="elemTypeColor(elem.element_type)" size="tiny" round>{{ elemTypeLabel(elem.element_type) }}</n-tag>
                      <n-text style="font-size:12px; flex:1">{{ elem.element_id }}</n-text>
                      <n-tag size="tiny" round>{{ elem.relation_type }}</n-tag>
                      <n-tag :type="elem.importance === 'major' ? 'error' : elem.importance === 'minor' ? 'default' : 'info'" size="tiny" round>
                        {{ importanceLabel(elem.importance) }}
                      </n-tag>
                    </div>
                    <n-button
                      v-if="!readOnly"
                      size="tiny"
                      type="error"
                      text
                      :loading="deletingId === elem.id"
                      @click="doDelete(elem)"
                    >删除</n-button>
                  </div>
                </n-space>

                <n-empty v-if="!loading && elements.length === 0 && !storyNodeNotFound" description="暂无关联元素" />
              </n-space>
            </n-spin>

            <n-card
              v-if="storyNodeId && !storyNodeNotFound && !readOnly"
              title="添加元素关联"
              size="small"
              :bordered="false"
              style="margin-top: 10px; border-top: 1px solid var(--n-divider-color, rgba(0,0,0,.07))"
            >
              <n-space vertical :size="8">
                <n-space :size="6" wrap>
                  <n-select
                    v-model:value="form.element_type"
                    :options="elementTypeOptions"
                    size="small"
                    style="width: 90px"
                    placeholder="类型"
                  />
                  <n-input
                    v-model:value="form.element_id"
                    size="small"
                    placeholder="元素 ID（人物/地点名称）"
                    style="flex: 1; min-width: 120px"
                  />
                </n-space>
                <n-space :size="6" wrap>
                  <n-select
                    v-model:value="form.relation_type"
                    :options="relationTypeOptions"
                    size="small"
                    style="width: 100px"
                    placeholder="关联类型"
                  />
                  <n-select
                    v-model:value="form.importance"
                    :options="importanceOptions"
                    size="small"
                    style="width: 80px"
                    placeholder="重要性"
                  />
                  <n-input
                    v-model:value="form.notes"
                    size="small"
                    placeholder="备注（可选）"
                    style="flex: 1; min-width: 80px"
                  />
                </n-space>
                <n-button
                  type="primary"
                  size="small"
                  :loading="adding"
                  :disabled="!form.element_type || !form.element_id || !form.relation_type"
                  @click="doAdd"
                >
                  添加关联
                </n-button>
              </n-space>
            </n-card>
          </n-card>

          <!-- 片场：本章伏笔回收建议（原右侧「片场 → 本章建议」） -->
          <n-card title="片场 · 本章伏笔回收建议" size="small" :bordered="true">
            <ForeshadowChapterSuggestionsPanel
              :slug="slug"
              :current-chapter-number="currentChapterNumber"
              embedded
            />
          </n-card>

          <!-- AI 审阅与质检（与「章节状态」同源，便于编辑时对照） -->
          <n-card
            v-if="lastWorkflowResult && qcChapterNumber != null"
            title="AI 审阅与质检（最近一次流式生成）"
            size="small"
            :bordered="true"
          >
            <n-space vertical :size="10">
              <n-alert
                v-if="currentChapterNumber !== qcChapterNumber"
                type="info"
                :show-icon="true"
                style="font-size: 12px"
              >
                以下为针对「第 {{ qcChapterNumber }} 章」的质检；当前浏览第 {{ currentChapterNumber }} 章时可作参考。
              </n-alert>
              <ConsistencyReportPanel
                :report="lastWorkflowResult.consistency_report"
                :token-count="lastWorkflowResult.token_count"
                @location-click="onLocationClick"
              />
              <n-collapse
                v-if="lastWorkflowResult.style_warnings && lastWorkflowResult.style_warnings.length > 0"
                class="cliche-collapse"
              >
                <n-collapse-item
                  :title="`俗套句式命中 ${lastWorkflowResult.style_warnings.length} 处`"
                  name="cliche"
                >
                  <n-space vertical :size="6">
                    <n-alert
                      v-for="(w, i) in lastWorkflowResult.style_warnings"
                      :key="i"
                      :type="w.severity === 'warning' ? 'warning' : 'info'"
                      :title="w.pattern"
                      style="font-size: 12px"
                    >
                      「{{ w.text }}」
                    </n-alert>
                  </n-space>
                </n-collapse-item>
              </n-collapse>
              <n-text depth="3" style="font-size: 11px">
                完整本章概览与清除摘要见「📋 章节状态」Tab。
              </n-text>
            </n-space>
          </n-card>
        </n-space>
      </n-scrollbar>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, onMounted, computed } from 'vue'
import { useMessage } from 'naive-ui'
import { chapterElementApi } from '../../api/chapterElement'
import type { ChapterElementDTO, ElementType, RelationType, Importance } from '../../api/chapterElement'
import { planningApi } from '../../api/planning'
import type { StoryNode } from '../../api/planning'
import type { GenerateChapterWorkflowResponse } from '../../api/workflow'
import ForeshadowChapterSuggestionsPanel from './ForeshadowChapterSuggestionsPanel.vue'
import ConsistencyReportPanel from './ConsistencyReportPanel.vue'

const props = withDefaults(
  defineProps<{
    slug: string
    currentChapterNumber?: number | null
    /** 托管运行时只读，不可增删元素 */
    readOnly?: boolean
    /** 与章节状态 Tab 一致的最近一次生成质检（可选展示） */
    lastWorkflowResult?: GenerateChapterWorkflowResponse | null
    qcChapterNumber?: number | null
  }>(),
  { currentChapterNumber: null, readOnly: false, lastWorkflowResult: null, qcChapterNumber: null }
)

const message = useMessage()

const elements = ref<ChapterElementDTO[]>([])
const loading = ref(false)
const adding = ref(false)
const deletingId = ref<string | null>(null)
const storyNodeId = ref<string | null>(null)
const storyNodeNotFound = ref(false)
const chapterPlan = ref<StoryNode | null>(null)
const filterType = ref<ElementType | undefined>(undefined)

const form = ref<{
  element_type: ElementType | undefined
  element_id: string
  relation_type: RelationType | undefined
  importance: Importance
  notes: string
}>({ element_type: undefined, element_id: '', relation_type: undefined, importance: 'normal', notes: '' })

const elementTypeOptions = [
  { label: '人物', value: 'character' },
  { label: '地点', value: 'location' },
  { label: '道具', value: 'item' },
  { label: '组织', value: 'organization' },
  { label: '事件', value: 'event' },
]

const relationTypeOptions = [
  { label: '出场', value: 'appears' },
  { label: '提及', value: 'mentioned' },
  { label: '场景', value: 'scene' },
  { label: '使用', value: 'uses' },
  { label: '参与', value: 'involved' },
  { label: '发生', value: 'occurs' },
]

const importanceOptions = [
  { label: '主要', value: 'major' },
  { label: '一般', value: 'normal' },
  { label: '次要', value: 'minor' },
]

const elemTypeLabel = (t: string) => elementTypeOptions.find(o => o.value === t)?.label ?? t
const elemTypeColor = (t: string): 'error' | 'warning' | 'info' | 'success' | 'default' => {
  const map: Record<string, 'error' | 'warning' | 'info' | 'success' | 'default'> = {
    character: 'error', location: 'success', item: 'warning', organization: 'info', event: 'default'
  }
  return map[t] ?? 'default'
}
const importanceLabel = (i: string) => importanceOptions.find(o => o.value === i)?.label ?? i

const groupedCharacters = computed(() =>
  elements.value.filter(e => e.element_type === 'character')
)
const groupedLocations = computed(() =>
  elements.value.filter(e => e.element_type === 'location')
)
const groupedOther = computed(() =>
  elements.value.filter(e => e.element_type !== 'character' && e.element_type !== 'location')
)

const planMoodLine = computed(() => {
  const m = chapterPlan.value?.metadata
  if (!m || typeof m !== 'object') return ''
  const mood = m.mood ?? m.emotion ?? m.tone
  if (typeof mood === 'string' && mood.trim()) return mood
  if (Array.isArray(m.moods) && m.moods.length) return m.moods.join('、')
  return ''
})

/** 在结构树森林中按章节号查找 chapter 节点 */
function findChapterNode(nodes: StoryNode[], num: number): StoryNode | null {
  for (const node of nodes) {
    if (node.node_type === 'chapter' && node.number === num) return node
    if (node.children?.length) {
      const found = findChapterNode(node.children, num)
      if (found) return found
    }
  }
  return null
}

const resolveStoryNode = async () => {
  storyNodeId.value = null
  chapterPlan.value = null
  storyNodeNotFound.value = false
  if (!props.currentChapterNumber) return
  try {
    const res = await planningApi.getStructure(props.slug)
    const roots = res.data?.nodes ?? []
    const node = findChapterNode(roots, props.currentChapterNumber)
    if (node) {
      storyNodeId.value = node.id
      chapterPlan.value = node
    } else {
      storyNodeNotFound.value = true
    }
  } catch {
    storyNodeNotFound.value = true
  }
}

const loadElements = async () => {
  if (!storyNodeId.value) return
  loading.value = true
  try {
    const res = await chapterElementApi.getElements(storyNodeId.value, filterType.value)
    elements.value = res.data
  } catch {
    message.error('加载章节元素失败')
  } finally {
    loading.value = false
  }
}

const doAdd = async () => {
  if (!storyNodeId.value || !form.value.element_type || !form.value.element_id || !form.value.relation_type) return
  adding.value = true
  try {
    const res = await chapterElementApi.addElement(storyNodeId.value, {
      element_type: form.value.element_type,
      element_id: form.value.element_id,
      relation_type: form.value.relation_type,
      importance: form.value.importance,
      notes: form.value.notes || undefined,
    })
    elements.value.push(res.data)
    form.value.element_id = ''
    form.value.notes = ''
    message.success('已添加')
  } catch (e: unknown) {
    const err = e as { response?: { data?: { detail?: string } } }
    message.error(err?.response?.data?.detail || '添加失败')
  } finally {
    adding.value = false
  }
}

const doDelete = async (elem: ChapterElementDTO) => {
  if (!storyNodeId.value) return
  deletingId.value = elem.id
  try {
    await chapterElementApi.deleteElement(storyNodeId.value, elem.id)
    elements.value = elements.value.filter(e => e.id !== elem.id)
    message.success('已删除')
  } catch {
    message.error('删除失败')
  } finally {
    deletingId.value = null
  }
}

function onLocationClick(location: number) {
  message.info(`问题位置约在第 ${location} 字附近，可在章节编辑中搜索或滚动查看。`)
}

watch(() => props.slug, async (slug) => {
  if (slug) {
    elements.value = []
    storyNodeId.value = null
    chapterPlan.value = null
    storyNodeNotFound.value = false
    await resolveStoryNode()
    await loadElements()
  }
})

watch(() => props.currentChapterNumber, async () => {
  await resolveStoryNode()
  await loadElements()
}, { immediate: false })

onMounted(async () => {
  await resolveStoryNode()
  await loadElements()
})
</script>

<style scoped>
.ce-panel {
  padding: 0;
  height: 100%;
  min-height: 0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
.ce-scroll {
  flex: 1;
  min-height: 0;
}
.ce-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 5px 8px;
  border-radius: 8px;
  background: rgba(0,0,0,.03);
  gap: 6px;
}
.ce-item-info {
  display: flex;
  align-items: center;
  gap: 5px;
  flex: 1;
  overflow: hidden;
  flex-wrap: wrap;
  font-size: 12px;
}
.cliche-collapse :deep(.n-collapse-item__header) {
  font-size: 13px;
}
</style>
