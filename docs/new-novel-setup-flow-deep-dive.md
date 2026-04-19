# 新书创建向导深度代码说明

本文是 [新书创建向导代码导读](/Users/sj/PlotPilot/docs/new-novel-setup-flow.md) 的细读版。

目标不是只说明“调了哪个接口”，而是把每个步骤里的代码职责拆开讲清楚：

- 前端状态是怎么流动的
- 发送了什么请求
- 后端拿到请求后做了哪些事
- 哪些地方会调用 LLM
- 结果最终写到了哪里
- 当前实现里有哪些隐藏副作用和未接线部分

## 阅读顺序

建议按这个顺序理解整条链路：

1. 创建小说
2. 打开新书设置向导
3. 世界观 + 文风
4. 人物
5. 地图
6. 主线候选
7. 选定主线并落库
8. 情节弧

---

## 1. 创建小说：从首页表单到 `novels` 表

### 涉及文件

- [frontend/src/views/Home.vue](/Users/sj/PlotPilot/frontend/src/views/Home.vue)
- [interfaces/api/v1/core/novels.py](/Users/sj/PlotPilot/interfaces/api/v1/core/novels.py)
- [application/core/services/novel_service.py](/Users/sj/PlotPilot/application/core/services/novel_service.py)

### 前端做了什么

首页“新建书目”的核心函数是 `handleCreate()`。

它做的事情非常直接：

1. 校验 `newBook.premise` 不能为空
2. 如果书名没填，就把梗概前 20 个字符当标题
3. 生成一个前端侧的 `novel_id`
4. 把 `title`、`author`、`target_chapters`、`premise` 打包成 payload
5. 调用 `novelApi.createNovel(payload)`
6. 成功后记录：
   - `newNovelId`
   - `newNovelTargetChapters`
   - `showSetupGuide = true`
7. 通过 `showSetupGuide` 打开向导组件

这里有两个实现细节值得注意：

- “类型”和“每章字数”虽然在 UI 里有输入框，但当前创建接口并没有提交这两个字段。
- `author` 现在不是用户输入，而是前端写死成 `"作者"`。

### 后端做了什么

`POST /api/v1/novels/` 由 [interfaces/api/v1/core/novels.py](/Users/sj/PlotPilot/interfaces/api/v1/core/novels.py) 的 `create_novel()` 处理。

这个接口当前只做一件事：创建小说实体，不做 AI 初始化。

服务层入口是 [application/core/services/novel_service.py](/Users/sj/PlotPilot/application/core/services/novel_service.py) 的 `create_novel()`。

它的逻辑是：

1. 用传入的参数构造 `Novel` 领域对象
2. 把 `stage` 初始设为 `NovelStage.PLANNING`
3. 通过 `self.novel_repository.save(novel)` 落库
4. 返回 `NovelDTO.from_domain(novel)`

### 这一步没有做什么

这一步不会：

- 自动生成 Bible
- 自动生成世界观
- 自动生成主线
- 自动生成情节弧

这些动作都交给随后弹出的向导来做。

---

## 2. 向导是怎么被拉起来的

### 涉及文件

- [frontend/src/views/Home.vue](/Users/sj/PlotPilot/frontend/src/views/Home.vue)
- [frontend/src/components/onboarding/NovelSetupGuide.vue](/Users/sj/PlotPilot/frontend/src/components/onboarding/NovelSetupGuide.vue)

### 触发机制

`Home.vue` 里有：

- `newNovelId`
- `newNovelTargetChapters`
- `showSetupGuide`

创建小说成功后：

- `newNovelId.value = result.id`
- `newNovelTargetChapters.value = targetChapters`
- `showSetupGuide.value = true`

模板里通过：

```vue
<NovelSetupGuide
  v-if="newNovelId"
  :novel-id="newNovelId"
  :target-chapters="newNovelTargetChapters"
  :show="showSetupGuide"
/>
```

把小说 ID 和目标章节数传进向导。

### 向导内部的状态模型

`NovelSetupGuide.vue` 内部主要靠这些状态管理流程：

- `currentStep`
- `generatingBible`
- `bibleGenerated`
- `generatingCharacters`
- `charactersGenerated`
- `generatingLocations`
- `locationsGenerated`
- `plotOptions`
- `mainPlotCommitted`

向导并不是一次性把所有步骤都跑完，而是：

- Step 1 在 `props.show` 打开时自动启动
- Step 2/3 通过 `handleNext()` 串行推进
- Step 4 进入页面时自动加载主线候选
- Step 5 当前只是说明页
- Step 6 结束并跳进工作台

---

## 3. 世界观 + 文风：Step 1 的完整执行链

### 涉及文件

- [frontend/src/components/onboarding/NovelSetupGuide.vue](/Users/sj/PlotPilot/frontend/src/components/onboarding/NovelSetupGuide.vue)
- [frontend/src/api/bible.ts](/Users/sj/PlotPilot/frontend/src/api/bible.ts)
- [frontend/src/api/worldbuilding.ts](/Users/sj/PlotPilot/frontend/src/api/worldbuilding.ts)
- [interfaces/api/v1/world/bible.py](/Users/sj/PlotPilot/interfaces/api/v1/world/bible.py)
- [application/world/services/auto_bible_generator.py](/Users/sj/PlotPilot/application/world/services/auto_bible_generator.py)
- [application/world/services/worldbuilding_service.py](/Users/sj/PlotPilot/application/world/services/worldbuilding_service.py)
- [interfaces/api/v1/world/worldbuilding_routes.py](/Users/sj/PlotPilot/interfaces/api/v1/world/worldbuilding_routes.py)

### 前端：`startBibleGeneration()` 做了什么

向导打开时，`watch(() => props.show, ...)` 会触发 `startBibleGeneration()`。

这个函数内部的结构大致是：

1. 清理已有定时器
2. 增加一个 `biblePollEpoch`，用于作废旧轮询
3. 设置：
   - `generatingBible = true`
   - `bibleError = ''`
4. 请求：

```ts
await bibleApi.generateBible(props.novelId, 'worldbuilding')
```

5. 启动串行轮询：

```ts
const status = await bibleApi.getBibleStatus(props.novelId)
```

6. 当 `status.ready` 为真时：
   - 加载 `bibleApi.getBible(props.novelId)`
   - 加载 `worldbuildingApi.getWorldbuilding(props.novelId)`
   - 如果 `worldbuilding` 独立接口失败，再从 `Bible.world_settings` 回退
   - 把两者 merge 成用于展示的 `worldbuildingData`

### 为什么要同时读 `Bible` 和 `Worldbuilding`

这是当前实现里比较关键的一个设计点。

世界观会落到两套存储：

1. `Worldbuilding` 表  
   用来支持后续 AI 生成人物、地图时读取五维结构
2. `Bible.world_settings`  
   用来兼容现有 Bible 体系和前端展示

所以前端展示时采取了“双来源 merge”策略：

- 有结构化 `Worldbuilding` 就优先用它
- 否则用 `Bible.world_settings` 还原

### 后端：接口层做了什么

`POST /api/v1/bible/novels/{novel_id}/generate?stage=worldbuilding`

这个接口的核心并不是同步返回生成结果，而是：

- 立即返回 `202 Accepted`
- 把真正的生成逻辑放进后台任务 `_generate_task()`

后台任务的主要步骤：

1. 根据 `novel_id` 读取小说
2. 从小说里拿：
   - `premise`
   - `title`
   - `target_chapters`
3. 调用：

```python
await bible_generator.generate_and_save(
    novel_id,
    premise,
    novel.target_chapters,
    stage=stage,
)
```

4. 把返回结果里的 `characters` / `locations` / `style` 拼成一个 `bible_summary`
5. 无论当前阶段是不是只生成世界观，都会继续调用：

```python
await knowledge_generator.generate_and_save(...)
```

### 这一步最重要的副作用

即使你只点了“世界观”，当前后台任务仍然会顺带跑一次 Knowledge 生成。

这意味着：

- Step 1 不只是生成世界观
- 它还会尝试初始化一部分知识图谱相关数据

### 服务层：`AutoBibleGenerator.generate_and_save(stage="worldbuilding")`

这一步真正的 AI 逻辑在 [application/world/services/auto_bible_generator.py](/Users/sj/PlotPilot/application/world/services/auto_bible_generator.py)。

在 `stage == "worldbuilding"` 分支中，它会：

1. 确保 Bible 记录存在
2. 调用 `_generate_worldbuilding_and_style(premise, target_chapters)`
3. 从返回 JSON 中提取：
   - `style`
   - `worldbuilding`
4. 把 `style` 写成一条 `style_note`
5. 调用 `_save_worldbuilding(...)`

### Prompt 逻辑

`_generate_worldbuilding_and_style()` 会给 LLM 一段明确的系统提示，要求生成：

- 5 维世界观
  - `core_rules`
  - `geography`
  - `society`
  - `culture`
  - `daily_life`
- `style`

这一步的返回值必须是一个 JSON 对象。

### `_call_llm_and_parse()` 做了什么

这是世界观、人物、地图三步共用的 LLM 包装逻辑。

它的职责是：

1. 构造 `Prompt(system=..., user=...)`
2. 创建 `GenerationConfig(max_tokens=2048, temperature=0.7)`
3. 调用 `self.llm_service.generate(prompt, config)`
4. 对返回文本做清洗：
   - 去掉代码块围栏
   - 截取第一个 `{` 到最后一个 `}`
5. `json.loads(...)`

也就是说，它假设 LLM 的输出最终能被裁剪成合法 JSON。

### `_save_worldbuilding()` 做了什么

这个函数实际上保存了两份数据。

#### 第 1 份：写入 `Worldbuilding` 表

它会调用 `worldbuilding_service.update_worldbuilding(...)`，把五维字段分别写到单独表结构里。

这份数据的主要用途是：

- 给 Step 2 “人物”
- 给 Step 3 “地图”
- 以及以后其他服务读取结构化世界观

#### 第 2 份：写入 `Bible.world_settings`

它还会遍历五维世界观，把每个字段拍平为：

- `core_rules.power_system`
- `society.politics`
- `daily_life.entertainment`

再通过 `BibleService.add_world_setting(...)` 写进去。

这份数据的主要用途是：

- 给旧的 Bible 体系继续使用
- 给前端回退展示

---

## 4. 人物：Step 2 的完整执行链

### 涉及文件

- [frontend/src/components/onboarding/NovelSetupGuide.vue](/Users/sj/PlotPilot/frontend/src/components/onboarding/NovelSetupGuide.vue)
- [interfaces/api/v1/world/bible.py](/Users/sj/PlotPilot/interfaces/api/v1/world/bible.py)
- [application/world/services/auto_bible_generator.py](/Users/sj/PlotPilot/application/world/services/auto_bible_generator.py)
- [application/world/services/bible_service.py](/Users/sj/PlotPilot/application/world/services/bible_service.py)

### 前端：Step 1 -> Step 2 的过渡

当用户在 Step 1 点击“确认并继续”时，`handleNext()` 进入 `currentStep === 1` 分支：

1. `currentStep = 2`
2. `generatingCharacters = true`
3. 请求：

```ts
await bibleApi.generateBible(props.novelId, 'characters')
```

4. 然后不断调用：

```ts
const bible = await bibleApi.getBible(props.novelId)
```

5. 当 `bible.characters.length > 0` 时：
   - `generatingCharacters = false`
   - `charactersGenerated = true`

前端这一步没有单独的“人物状态接口”，而是直接把 Bible 结果当人物生成完成信号。

### 后端：人物生成接口仍然复用 Bible 生成接口

这一步没有单独的人物 API。

仍然是：

- `POST /api/v1/bible/novels/{novel_id}/generate?stage=characters`

后台任务 `_generate_task()` 不变，只是把 `stage` 传成 `characters`。

### 服务层：`generate_and_save(stage="characters")`

这一步的执行顺序是：

1. 确保 Bible 存在
2. 调用 `_load_worldbuilding(novel_id)`  
   从 `Worldbuilding` 表读回五维世界观
3. 调用 `_generate_characters(premise, target_chapters, existing_worldbuilding)`
4. 遍历返回的 `characters`
5. 逐个调用 `BibleService.add_character(...)` 落库

### `_generate_characters()` 的输入结构

这个函数不会直接把原始世界观对象传给模型，而是先通过 `_summarize_worldbuilding(worldbuilding)` 把 5 维对象压成一段摘要文本。

换句话说，这一步不是“模型直接看 JSON 世界观”，而是“模型看一段总结后的文本世界观”。

### `_generate_characters()` 的输出结构

Prompt 要求输出：

```json
{
  "characters": [
    {
      "name": "人物名",
      "role": "主角/配角/对手/导师",
      "description": "单行描述",
      "relationships": [...]
    }
  ]
}
```

### 人物保存时做了什么

在 `generate_and_save(stage="characters")` 里，保存人物时会：

1. 为每个角色构造 `character_id`
2. 处理重复 ID
3. 调 `BibleService.add_character(...)`
4. 成功后收集到 `character_ids`

如果配置了 `triple_repository`，后面还会：

```python
await self._generate_character_triples(novel_id, character_ids)
```

也就是说，这一步不只是写角色卡，还可能顺带生成人物关系三元组。

---

## 5. 地图：Step 3 的完整执行链

### 涉及文件

- [frontend/src/components/onboarding/NovelSetupGuide.vue](/Users/sj/PlotPilot/frontend/src/components/onboarding/NovelSetupGuide.vue)
- [application/world/services/auto_bible_generator.py](/Users/sj/PlotPilot/application/world/services/auto_bible_generator.py)
- [application/world/services/bible_service.py](/Users/sj/PlotPilot/application/world/services/bible_service.py)

### 前端：Step 2 -> Step 3 的过渡

当用户在 Step 2 点击“确认并继续”时，`handleNext()` 进入 `currentStep === 2` 分支：

1. `currentStep = 3`
2. `generatingLocations = true`
3. 请求：

```ts
await bibleApi.generateBible(props.novelId, 'locations')
```

4. 然后循环读取 `bibleApi.getBible(props.novelId)`
5. 当 `bible.locations.length > 0` 时，认为地图生成完成

### 服务层：`generate_and_save(stage="locations")`

这个分支会：

1. 确保 Bible 记录存在
2. 读取已有世界观 `_load_worldbuilding(novel_id)`
3. 读取已有人物 `_load_characters(novel_id)`
4. 调用：

```python
await self._generate_locations(premise, target_chapters, existing_worldbuilding, existing_characters)
```

5. 保存地点到 Bible

### `_generate_locations()` 如何构造提示词

这一步会输入两类上下文：

1. 世界观摘要 `wb_summary`
2. 人物摘要 `char_summary`

其中 `char_summary` 是把已有人物裁成：

- 名字
- 描述前 50 个字符

再拼成一段列表文本。

这样做的意思是让模型在生成地图时：

- 不只看世界观
- 还考虑“人物会在哪里活动”

### 地图返回结构

Prompt 要求输出：

```json
{
  "locations": [
    {
      "id": "稳定id",
      "name": "地点名",
      "type": "城市/建筑/区域/特殊场所",
      "description": "单行描述",
      "parent_id": null,
      "connections": [...]
    }
  ]
}
```

这里有两个关键设计：

- `parent_id` 表示层级关系
- `connections` 表示非树状连接关系

### 地图保存时做了什么

保存地点时，代码会：

1. 为每个地点确定 `location_id`
2. 处理重复 ID
3. 调 `BibleService.add_location(...)`
4. 收集 `location_ids`
5. 如果配置了 `triple_repository`，调用 `_generate_location_triples(...)`

所以地图这一步的输出不只是 UI 预览，还会影响：

- Bible 地点树
- 地点关系三元组

### 这一步为什么更容易出脏数据问题

因为地点对象要求的字段更多：

- `id`
- `name`
- `type`
- `description`
- `parent_id`
- `connections`

一旦模型只返回了部分字段，保存逻辑就更容易在“字段缺失”时抛错。

---

## 6. 主线候选：Step 4 的完整执行链

### 涉及文件

- [frontend/src/components/onboarding/NovelSetupGuide.vue](/Users/sj/PlotPilot/frontend/src/components/onboarding/NovelSetupGuide.vue)
- [frontend/src/api/workflow.ts](/Users/sj/PlotPilot/frontend/src/api/workflow.ts)
- [interfaces/api/v1/engine/generation.py](/Users/sj/PlotPilot/interfaces/api/v1/engine/generation.py)
- [application/blueprint/services/setup_main_plot_suggestion_service.py](/Users/sj/PlotPilot/application/blueprint/services/setup_main_plot_suggestion_service.py)

### 前端：什么时候开始拉主线候选

不是点击按钮后才拉，而是：

```ts
watch(currentStep, (step) => {
  if (step === 4 && props.show && plotOptions.value.length === 0 && !plotSuggesting.value) {
    void loadPlotSuggestions()
  }
})
```

也就是说：

- 一进入 Step 4
- 如果当前没有候选
- 就自动请求后端推演

### 前端：如何展示和提交

`loadPlotSuggestions()` 调的是：

```ts
workflowApi.suggestMainPlotOptions(props.novelId)
```

返回的是 `plot_options` 数组，每一项包含：

- `id`
- `type`
- `title`
- `logline`
- `core_conflict`
- `starting_hook`

用户有两种选择：

1. 选系统给的一条
2. 自己写一句主线

### 后端：主线候选推演接口

路由在 [interfaces/api/v1/engine/generation.py](/Users/sj/PlotPilot/interfaces/api/v1/engine/generation.py)：

- `POST /api/v1/novels/{novel_id}/setup/suggest-main-plot-options`

这个接口只做两件事：

1. 检查小说存在
2. 调 `setup_svc.suggest_options(novel_id)`

### 服务层：`SetupMainPlotSuggestionService.suggest_options()`

这是 Step 4 的核心。

它的实现分成三个阶段：

#### 阶段 A：组上下文 `_build_context()`

它会把多个来源聚合成一个上下文对象：

- 小说标题
- 梗概
- 目标章节数
- 主角
- 其他人物
- 地点
- 世界观摘要
- 文风提示

这里的特点是：

- 主角会优先找 `role` 里包含“主角”的角色
- 如果找不到，就用人物列表第一位兜底
- 风格提示来自 `style_notes`

#### 阶段 B：喂给 LLM 推演三条候选

`system_prompt` 中规定得非常严格：

- 必须恰好输出 3 条
- 顺序分别对应：
  - A：自下而上的爆发
  - B：自上而下的阴谋
  - C：异类 / 变数觉醒
- 只输出合法 JSON

这一步返回的是“候选”，不是正式故事线。

#### 阶段 C：解析和兜底

模型返回后会经过：

- `_parse_plot_json()`
- `_normalize_options()`

如果：

- JSON 解析失败
- 数量不足 3 条

服务会用 `_fallback_options(ctx)` 补足，甚至整包回退。

这意味着主线候选这一步有比较明确的容错设计，不会因为 LLM 偶尔格式不稳就让 UI 完全空掉。

---

## 7. 选定主线：从候选结果变成 Storyline 记录

### 涉及文件

- [frontend/src/components/onboarding/NovelSetupGuide.vue](/Users/sj/PlotPilot/frontend/src/components/onboarding/NovelSetupGuide.vue)
- [frontend/src/api/workflow.ts](/Users/sj/PlotPilot/frontend/src/api/workflow.ts)
- [interfaces/api/v1/engine/generation.py](/Users/sj/PlotPilot/interfaces/api/v1/engine/generation.py)
- [domain/novel/services/storyline_manager.py](/Users/sj/PlotPilot/domain/novel/services/storyline_manager.py)

### 前端：不是保存“候选对象”，而是创建一条正式故事线

用户选中某个候选时，`adoptPlotOption(opt)` 不会把整个 `opt` 原样存下。

它会先把候选的几个字段拼成一段描述：

- `logline`
- `core_conflict`
- `starting_hook`

然后调：

```ts
workflowApi.createStoryline(props.novelId, {
  storyline_type: 'main_plot',
  estimated_chapter_start: 1,
  estimated_chapter_end: chapterEndForStoryline.value,
  name: opt.title,
  description: parts.join('\n\n'),
})
```

如果用户选择“我有自己的想法”，`adoptCustomMainPlot()` 也是同理，只是描述内容来自用户输入。

### 后端：`POST /storylines`

接口在 [interfaces/api/v1/engine/generation.py](/Users/sj/PlotPilot/interfaces/api/v1/engine/generation.py)：

- `POST /api/v1/novels/{novel_id}/storylines`

路由层做的事不复杂：

1. 把字符串 `storyline_type` 转成 `StorylineType`
2. 调 `manager.create_storyline(...)`
3. 再把领域对象转成响应 DTO

### 领域服务：`StorylineManager.create_storyline()`

真正的保存动作在 [domain/novel/services/storyline_manager.py](/Users/sj/PlotPilot/domain/novel/services/storyline_manager.py)。

它会：

1. 生成 `storyline_id`
2. 构造 `Storyline` 领域对象
3. 默认状态设为 `StorylineStatus.ACTIVE`
4. 调 `self.repository.save(storyline)`

所以 Step 4 的意义是：

- 前半段：LLM 给你“可选的主线方向”
- 后半段：用户把其中一条确认成“正式主线记录”

---

## 8. 情节弧：向导里的 Step 5 和真实实现是分开的

### 向导里的 Step 5 当前做了什么

文件：`frontend/src/components/onboarding/NovelSetupGuide.vue`

Step 5 当前只有说明文案：

- 开端
- 上升
- 转折
- 高潮
- 结局

而 `handleNext()` 在 `currentStep === 5` 时只是简单进入 Step 6。

所以：

- 没有请求
- 没有调用 `workflowApi.getPlotArc`
- 没有调用 `workflowApi.createPlotArc`
- 没有任何 PlotArc 落库

### 情节弧真正在哪里实现

真实的情节弧编辑入口在工作台，而不是向导：

- 前端：`frontend/src/components/workbench/PlotArcPanel.vue`
- API：`frontend/src/api/workflow.ts`
  - `getPlotArc(novelId)`
  - `createPlotArc(novelId, data)`
- 后端：`interfaces/api/v1/engine/generation.py`
  - `GET /api/v1/novels/{novel_id}/plot-arc`
  - `POST /api/v1/novels/{novel_id}/plot-arc`

### 后端 PlotArc 路由做了什么

`GET /plot-arc`：

- 从 `PlotArcRepository` 读取当前小说的情节弧
- 转成 `PlotArcResponse`

`POST /plot-arc`：

1. 先尝试读取现有情节弧
2. 如果没有，就新建一个 `PlotArc`
3. 清空旧的 `key_points`
4. 把请求里的 `key_points` 全部重建成 `PlotPoint`
5. `repository.save(plot_arc)`

所以当前的情节弧编辑是“整包覆盖式保存”，不是增量 patch。

### 还有一条自动剧情点生成路径

除了手工编辑，系统里还有自动补剧情点的逻辑：

- 文件：`application/world/services/chapter_narrative_sync.py`
- 函数：`_auto_generate_plot_point(...)`

这个函数会根据：

- 当前章节张力分数
- 与上一章张力的差值

自动判断要不要新增：

- `RISING_ACTION`
- `TURNING_POINT`
- `CLIMAX`
- `FALLING_ACTION`
- `RESOLUTION`

然后写回 PlotArc。

所以当前 PlotArc 有两条来源：

1. 工作台手工编辑
2. 章后自动分析补点

但它们都不在新书创建向导 Step 5 里触发。

---

## 9. 这条向导链路里的几个“隐藏副作用”

### 1. Step 1 不只是生成世界观

虽然 UI 文案写的是世界观 + 文风，但后台任务还会顺带跑 Knowledge 生成。

### 2. 世界观其实写了两份

不是只有 `Worldbuilding`，还会写到 `Bible.world_settings`。

### 3. 人物和地图生成都依赖前一步输出

- 人物依赖已保存的世界观
- 地图依赖世界观 + 人物

所以这三个步骤实际上是串行依赖链。

### 4. 主线候选本身不是“主线”

只有调用 `createStoryline()` 之后，才真正形成系统里的主故事线。

### 5. 情节弧向导里目前没有真正实现

它在产品流程上看起来像一步，但在代码里仍然只是说明页。

---

## 10. 给开发者的简化心智模型

如果把这套向导代码压缩成一句话，可以这样理解：

- `Home.vue` 只负责“建档”
- `NovelSetupGuide.vue` 负责“串起一连串初始化动作”
- `AutoBibleGenerator` 负责“世界观 / 人物 / 地图”三段式 AI 初始化
- `SetupMainPlotSuggestionService` 负责“给主线候选”
- `StorylineManager` 负责“把主线候选正式落库”
- `PlotArc` 目前不在向导里生成，而是在工作台维护

---

## 11. 后续如果继续完善，最自然的扩展点

### 给 Step 5 接真正的情节弧逻辑

可选方案：

1. 直接把 `PlotArcPanel` 精简版嵌进向导
2. 新增一个“AI 生成初版 PlotArc”接口
3. 在 Step 4 选定主线后，自动给出一版默认情节弧草稿

### 减少跨步骤的隐式副作用

当前 Step 1 还会触发 Knowledge 初始化，这会让“世界观”步骤的职责变得不纯。

如果要更清晰，可以把 Knowledge 初始化改成：

- 单独步骤
- 或在世界观 / 人物 / 地图全部确认后统一触发

### 统一世界观来源

现在前端同时依赖：

- `Worldbuilding` 表
- `Bible.world_settings`

长期看可以考虑把 `Bible.world_settings` 变成纯展示镜像，或者逐步只保留一个权威来源。

