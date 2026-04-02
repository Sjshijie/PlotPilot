<template>
  <div class="kb-root">
    <div class="kb-toolbar">
      <n-text depth="3" class="kb-hint">
        知识库：管理全书知识三元组，支持图谱可视化、JSON 编辑和表格编辑
      </n-text>
      <n-space :size="8">
        <n-button
          v-if="viewMode === 'editor'"
          type="primary"
          size="small"
          :loading="saving"
          @click="save"
        >
          保存
        </n-button>
        <n-button size="small" quaternary :loading="loading" @click="reload">刷新</n-button>
      </n-space>
    </div>

    <n-tabs v-model:value="viewMode" type="line" size="small" animated class="kb-tabs">
      <n-tab-pane name="graph" tab="图谱">
        <div v-if="emptyHint" class="kb-empty">
          <n-empty description="尚无三元组，可在「可视化编辑」中添加或由 kg_upsert_fact 写入" size="small" />
        </div>
        <GraphChart v-else :nodes="graphData.nodes" :links="graphData.links" height="calc(100vh - 200px)" />
      </n-tab-pane>

      <n-tab-pane name="json" tab="JSON">
        <n-input
          v-model:value="jsonText"
          type="textarea"
          :autosize="{ minRows: 20, maxRows: 40 }"
          placeholder="JSON 格式的三元组数据"
          class="kb-json-editor"
          :status="jsonError ? 'error' : undefined"
        />
        <n-text v-if="jsonError" type="error" depth="3" style="font-size: 12px; margin-top: 8px; display: block;">
          {{ jsonError }}
        </n-text>
        <n-space :size="8" style="margin-top: 12px;">
          <n-button size="small" @click="formatJson">格式化</n-button>
          <n-button size="small" type="primary" :loading="saving" @click="saveJson">保存 JSON</n-button>
        </n-space>
      </n-tab-pane>

      <n-tab-pane name="editor" tab="可视化编辑">
        <section class="kb-section">
          <div class="kb-section-head">
            <span class="kb-section-icon">◎</span>
            <span class="kb-section-title">知识三元组</span>
            <n-tag size="tiny" round :bordered="false" class="kb-tag-tool">kg_upsert_fact</n-tag>
          </div>
          <p class="kb-section-hint">
            事实型约束；主语/宾语可与人物图谱姓名对应，并标注出处章号。
            <strong>人物关系规范：</strong>人物节点用「主—是—主角/配角」，关系用「张三—师徒/父子/朋友—李四」。
          </p>

          <div class="kb-facts">
            <div v-for="(f, fi) in facts" :key="f.id" class="kb-fact">
              <div class="kb-fact-id">{{ f.id }}</div>
              <div class="kb-fact-grid">
                <n-input v-model:value="f.subject" placeholder="主语" size="small" />
                <n-input v-model:value="f.predicate" placeholder="关系" size="small" />
                <n-input v-model:value="f.object" placeholder="宾语" size="small" />
                <n-input-number
                  v-model:value="f.chapter_id"
                  placeholder="章号"
                  size="small"
                  :min="1"
                  :show-button="false"
                  class="kb-fact-ch"
                />
                <n-input v-model:value="f.note" placeholder="备注" size="small" class="kb-fact-note" />
              </div>
              <n-button size="tiny" quaternary type="error" @click="removeFact(fi)">删除</n-button>
            </div>
          </div>
          <n-button dashed block class="kb-add-fact" @click="addFact">+ 添加三元组</n-button>
        </section>
      </n-tab-pane>
    </n-tabs>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted, nextTick } from 'vue'
import { useMessage } from 'naive-ui'
import { knowledgeApi } from '../api/knowledge'
import GraphChart from './charts/GraphChart.vue'
import { convertGraph, type VisNode, type VisEdge, type EChartsGraphData } from '../utils/visToEcharts'

const props = defineProps<{ slug: string }>()
const message = useMessage()

interface Fact {
  id: string
  subject: string
  predicate: string
  object: string
  chapter_id?: number | null
  note?: string
}

const viewMode = ref<'graph' | 'json' | 'editor'>('graph')
const loading = ref(false)
const saving = ref(false)
const facts = ref<Fact[]>([])
const jsonText = ref('')
const jsonError = ref('')
const graphData = ref<EChartsGraphData>({ nodes: [], links: [] })

const emptyHint = computed(() => facts.value.length === 0 && !loading.value)

const buildVisData = () => {
  const labelToId = new Map<string, string>()
  let nextN = 0

  const entityId = (raw: string) => {
    const label = (raw || '').trim() || '（空）'
    if (!labelToId.has(label)) {
      labelToId.set(label, `ent_${nextN++}`)
    }
    return labelToId.get(label)!
  }

  const nodeSeen = new Set<string>()
  const nodes: VisNode[] = []
  const edges: VisEdge[] = []

  for (const f of facts.value) {
    const sid = entityId(f.subject)
    const oid = entityId(f.object)
    if (!nodeSeen.has(sid)) {
      nodeSeen.add(sid)
      const lab = (f.subject || '').trim() || '（空）'
      nodes.push({
        id: sid,
        label: lab.length > 42 ? `${lab.slice(0, 40)}…` : lab,
        title: lab,
        color: { background: '#e0e7ff', border: '#6366f1' },
        font: { size: 13 },
      })
    }
    if (!nodeSeen.has(oid)) {
      nodeSeen.add(oid)
      const lab = (f.object || '').trim() || '（空）'
      nodes.push({
        id: oid,
        label: lab.length > 42 ? `${lab.slice(0, 40)}…` : lab,
        title: lab,
        color: { background: '#fce7f3', border: '#db2777' },
        font: { size: 13 },
      })
    }
    const pred = (f.predicate || '').trim() || '—'
    const ch = f.chapter_id != null && f.chapter_id >= 1 ? `第${f.chapter_id}章` : ''
    const tip = [pred, f.note, ch].filter(Boolean).join('\n')
    edges.push({
      id: f.id,
      from: sid,
      to: oid,
      label: pred.length > 28 ? `${pred.slice(0, 26)}…` : pred,
      title: tip,
      arrows: 'to',
      font: { size: 11, align: 'middle' },
    })
  }

  return convertGraph(nodes, edges)
}

const redraw = async () => {
  await nextTick()
  graphData.value = buildVisData()
}

const reload = async () => {
  loading.value = true
  try {
    const data = await knowledgeApi.getKnowledge(props.slug)
    facts.value = data.facts || []
    jsonText.value = JSON.stringify(data.facts || [], null, 2)
    jsonError.value = ''
    await redraw()
  } catch (e: any) {
    message.error(e?.response?.data?.detail || '加载失败')
  } finally {
    loading.value = false
  }
}

const addFact = () => {
  const newId = `fact_${Date.now()}_${Math.random().toString(36).slice(2, 7)}`
  facts.value.push({
    id: newId,
    subject: '',
    predicate: '',
    object: '',
    chapter_id: null,
    note: '',
  })
}

const removeFact = (index: number) => {
  facts.value.splice(index, 1)
}

const save = async () => {
  saving.value = true
  try {
    await knowledgeApi.putKnowledge(props.slug, {
      version: 1,
      premise_lock: '',
      chapters: [],
      facts: facts.value,
    })
    message.success('已保存')
    await reload()
  } catch (e: any) {
    message.error(e?.response?.data?.detail || '保存失败')
  } finally {
    saving.value = false
  }
}

const formatJson = () => {
  try {
    const parsed = JSON.parse(jsonText.value)
    jsonText.value = JSON.stringify(parsed, null, 2)
    jsonError.value = ''
  } catch (e: any) {
    jsonError.value = `JSON 格式错误: ${e.message}`
  }
}

const saveJson = async () => {
  try {
    const parsed = JSON.parse(jsonText.value)
    if (!Array.isArray(parsed)) {
      jsonError.value = 'JSON 必须是数组格式'
      return
    }
    facts.value = parsed
    jsonError.value = ''
    await save()
  } catch (e: any) {
    jsonError.value = `JSON 格式错误: ${e.message}`
  }
}

watch(() => facts.value, redraw, { deep: true })

onMounted(() => {
  void reload()
})
</script>

<style scoped>
.kb-root {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: #fff;
}

.kb-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  border-bottom: 1px solid #e5e7eb;
  flex-shrink: 0;
}

.kb-hint {
  font-size: 13px;
}

.kb-tabs {
  flex: 1;
  overflow: hidden;
}

.kb-tabs :deep(.n-tabs-pane-wrapper) {
  padding: 16px;
  overflow-y: auto;
  height: calc(100vh - 200px);
}

.kb-empty {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 400px;
}

.kb-json-editor {
  font-family: 'Consolas', 'Monaco', monospace;
  font-size: 13px;
}

.kb-section {
  max-width: 1200px;
}

.kb-section-head {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}

.kb-section-icon {
  font-size: 16px;
  color: #6366f1;
}

.kb-section-title {
  font-size: 14px;
  font-weight: 600;
  color: #1f2937;
}

.kb-tag-tool {
  font-size: 11px;
  background: #f3f4f6;
  color: #6b7280;
}

.kb-section-hint {
  font-size: 12px;
  color: #6b7280;
  margin: 0 0 16px 0;
  line-height: 1.6;
}

.kb-facts {
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin-bottom: 16px;
}

.kb-fact {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 12px;
  background: #f9fafb;
  border-radius: 8px;
  border: 1px solid #e5e7eb;
}

.kb-fact-id {
  font-size: 11px;
  color: #9ca3af;
  font-family: monospace;
  min-width: 120px;
  padding-top: 6px;
}

.kb-fact-grid {
  display: grid;
  grid-template-columns: 1fr 1fr 1fr 100px 1.5fr;
  gap: 8px;
  flex: 1;
}

.kb-fact-ch {
  width: 100px;
}

.kb-fact-note {
  grid-column: span 2;
}

.kb-add-fact {
  margin-top: 8px;
}
</style>
