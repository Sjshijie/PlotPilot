# aitext 全面架构重构设计文档

**项目**: aitext - AI驱动的小说创作系统
**功能**: 后端 Web 层 + 核心 AI 模块的 DDD 架构重构
**日期**: 2026-03-31
**版本**: 1.0

---

## 目录

1. [概述](#概述)
2. [设计决策](#设计决策)
3. [架构设计](#架构设计)
4. [API 重新设计](#api-重新设计)
5. [领域模型](#领域模型)
6. [TDD 测试策略](#tdd-测试策略)
7. [旧代码清理](#旧代码清理)
8. [前端适配](#前端适配)
9. [实施路线图](#实施路线图)
10. [风险管理](#风险管理)

---

## 概述

### 项目背景

aitext 是一个 AI 驱动的长篇小说创作系统，当前架构存在以下问题：

**后端问题：**
- `web/app.py` 单体文件 762 行，包含 30+ 个路由端点
- 路由、业务逻辑、数据访问混在一起
- 缺少清晰的分层架构
- 难以测试和扩展

**核心 AI 模块问题：**
- `clients/llm.py` (222行)、`pipeline/runner.py` (357行)、`story/engine.py` (498行)
- 职责不清晰，耦合度高
- 缺少统一的抽象层
- 难以切换不同的 LLM 提供商

### 重构目标

1. **可维护性** - 代码清晰、易于理解和修改
2. **可扩展性** - 方便添加新功能、新模型
3. **性能** - 优化响应速度、减少重复计算
4. **测试覆盖** - TDD 驱动，测试覆盖率 > 80%

### 重构范围

**包含：**
- ✅ Web 层完全重构（路由、服务、仓储分离）
- ✅ AI 核心模块重构（LLM、Pipeline、Story Engine）
- ✅ API 完全重新设计（RESTful 规范）
- ✅ 前端适配（API 调用更新）
- ✅ 旧代码清理

**不包含：**
- ❌ 统计模块（已在 Week 2 完成模块化，保持现状）
- ❌ 前端组件重构（Week 2 已完成）
- ❌ 数据库迁移（本次仍使用文件系统，但抽象存储层）

---

## 设计决策

### 核心决策记录

| 决策点 | 选择 | 理由 |
|--------|------|------|
| 架构模式 | DDD 分层架构 | 平衡可维护性、扩展性、性能 |
| API 设计 | 完全重新设计 | 采用 RESTful 最佳实践 |
| 测试策略 | TDD（测试驱动开发） | 确保重构质量，覆盖率 > 80% |
| 存储抽象 | 抽象存储层 | 支持文件/数据库/对象存储 |
| 实施方式 | 并行开发 | Web 层和 AI 层同时重构 |
| 统计模块 | 保持现状 | 下阶段优化，本次不动 |
| 版本策略 | 单版本切换 | 新项目，无需双版本共存 |

### 技术栈选择

**后端框架：**
- FastAPI - Web 框架
- Pydantic - 数据验证
- dependency-injector - 依赖注入
- pytest - 测试框架

**前端框架：**
- Vue 3 + TypeScript
- Pinia - 状态管理
- Axios - HTTP 客户端

**AI 技术：**
- Anthropic Claude / ARK - LLM 提供商
- httpx - HTTP 客户端

---

## 架构设计

### 整体分层结构

```
aitext/
├── domain/                    # 领域层（核心业务逻辑）
│   ├── novel/                 # 小说聚合根
│   │   ├── entities/          # 实体
│   │   │   ├── novel.py       # 小说实体
│   │   │   ├── chapter.py     # 章节实体
│   │   │   └── manuscript.py  # 手稿实体
│   │   ├── value_objects/     # 值对象
│   │   │   ├── novel_id.py
│   │   │   ├── chapter_content.py
│   │   │   └── word_count.py
│   │   ├── services/          # 领域服务
│   │   │   └── chapter_validator.py
│   │   └── repositories/      # 仓储接口（只定义接口）
│   │       ├── novel_repository.py
│   │       └── chapter_repository.py
│   │
│   ├── bible/                 # 设定聚合根
│   │   ├── entities/
│   │   │   ├── bible.py
│   │   │   ├── character.py
│   │   │   └── world_setting.py
│   │   └── repositories/
│   │       └── bible_repository.py
│   │
│   ├── ai/                    # AI 领域
│   │   ├── entities/
│   │   │   ├── generation_task.py
│   │   │   └── llm_conversation.py
│   │   ├── value_objects/
│   │   │   ├── prompt.py
│   │   │   └── token_usage.py
│   │   ├── services/
│   │   │   ├── llm_service.py      # 领域服务接口
│   │   │   └── prompt_builder.py
│   │   └── repositories/
│   │       └── conversation_repository.py
│   │
│   └── shared/                # 共享内核
│       ├── events.py          # 领域事件
│       ├── exceptions.py      # 领域异常
│       └── specifications.py  # 规约模式
│
├── application/               # 应用层（用例编排）
│   ├── commands/              # 命令（写操作）
│   │   ├── create_novel.py
│   │   ├── write_chapter.py
│   │   └── generate_with_ai.py
│   ├── queries/               # 查询（读操作）
│   │   ├── get_novel_detail.py
│   │   └── list_chapters.py
│   ├── services/              # 应用服务
│   │   ├── novel_service.py
│   │   ├── chapter_service.py
│   │   └── ai_generation_service.py
│   └── dto/                   # 数据传输对象
│       ├── novel_dto.py
│       └── chapter_dto.py
│
├── infrastructure/            # 基础设施层（技术实现）
│   ├── persistence/           # 持久化实现
│   │   ├── repositories/      # 仓储实现
│   │   │   ├── file_novel_repository.py
│   │   │   ├── db_novel_repository.py
│   │   │   └── cache_novel_repository.py
│   │   ├── storage/           # 存储抽象
│   │   │   ├── storage_backend.py  # 接口
│   │   │   ├── file_storage.py
│   │   │   ├── s3_storage.py
│   │   │   └── db_storage.py
│   │   └── mappers/           # 数据映射器
│   │       └── novel_mapper.py
│   │
│   ├── ai/                    # AI 基础设施
│   │   ├── llm_client_impl.py # LLM 客户端实现
│   │   ├── providers/         # 不同提供商
│   │   │   ├── anthropic_provider.py
│   │   │   ├── ark_provider.py
│   │   │   └── openai_provider.py
│   │   └── streaming/
│   │       └── sse_streamer.py
│   │
│   ├── messaging/             # 消息/事件总线
│   │   ├── event_bus.py
│   │   └── task_queue.py
│   │
│   └── config/                # 配置管理
│       └── settings.py
│
├── interfaces/                # 接口层（对外暴露）
│   ├── api/                   # REST API
│   │   ├── v1/
│   │   │   ├── novels.py
│   │   │   ├── chapters.py
│   │   │   ├── bible.py
│   │   │   └── ai_tasks.py
│   │   ├── dependencies.py    # FastAPI 依赖注入
│   │   └── middleware/
│   │       ├── error_handler.py
│   │       └── logging.py
│   │
│   └── cli/                   # 命令行接口
│       └── commands.py
│
└── tests/                     # 测试（TDD）
    ├── unit/                  # 单元测试
    │   ├── domain/
    │   └── application/
    ├── integration/           # 集成测试
    └── e2e/                   # 端到端测试
```

### 分层职责

**领域层（Domain）：**
- 纯业务逻辑，不依赖任何外部框架
- 聚合根管理一致性边界
- 通过仓储接口访问数据（不关心实现）
- 发布领域事件

**应用层（Application）：**
- 编排领域对象完成用例
- 事务边界在这一层
- 调用领域服务和仓储
- 处理命令和查询

**基础设施层（Infrastructure）：**
- 实现领域层定义的接口
- 处理技术细节（数据库、文件、网络）
- 可替换的实现
- 外部服务集成

**接口层（Interfaces）：**
- 对外暴露 API
- 处理 HTTP 请求/响应
- 依赖注入配置
- 中间件处理

### 依赖关系

```
┌─────────────┐
│ Interfaces  │ ──┐
└─────────────┘   │
                  ↓
┌─────────────┐   ┌─────────────┐
│ Application │ → │   Domain    │
└─────────────┘   └─────────────┘
       ↓                 ↑
┌─────────────┐          │
│Infrastructure│ ─────────┘
└─────────────┘

依赖方向：外层依赖内层
Domain 层不依赖任何外层
```

---

## API 重新设计

### 设计原则

1. **RESTful 规范** - 资源导向，使用标准 HTTP 方法
2. **版本控制** - `/api/v1/` 前缀，方便未来升级
3. **统一响应格式** - 成功/失败都有一致的结构
4. **资源嵌套** - 合理的资源层级关系
5. **语义化命名** - 使用清晰的资源名称

### 统一响应格式

**成功响应：**
```json
{
  "success": true,
  "data": {
    "id": "novel-123",
    "title": "测试小说"
  },
  "meta": {
    "timestamp": "2026-03-31T10:00:00Z",
    "version": "v1"
  }
}
```

**错误响应：**
```json
{
  "success": false,
  "error": {
    "code": "NOVEL_NOT_FOUND",
    "message": "小说不存在",
    "details": {
      "novel_id": "novel-123"
    }
  },
  "meta": {
    "timestamp": "2026-03-31T10:00:00Z",
    "version": "v1"
  }
}
```

### API 端点对比

#### 小说（Novel）资源

| 功能 | 旧 API | 新 API | HTTP 方法 |
|------|--------|--------|-----------|
| 获取书籍列表 | `GET /api/books` | `GET /api/v1/novels` | GET |
| 获取书籍详情 | `GET /api/book/{slug}/desk` | `GET /api/v1/novels/{id}` | GET |
| 创建书籍 | `POST /api/jobs/create-book` | `POST /api/v1/novels` | POST |
| 更新书籍 | - | `PUT /api/v1/novels/{id}` | PUT |
| 删除书籍 | `DELETE /api/book/{slug}` | `DELETE /api/v1/novels/{id}` | DELETE |

#### 章节（Chapter）资源

| 功能 | 旧 API | 新 API | HTTP 方法 |
|------|--------|--------|-----------|
| 获取章节列表 | - | `GET /api/v1/novels/{id}/chapters` | GET |
| 获取章节内容 | `GET /api/book/{slug}/chapter/{cid}/body` | `GET /api/v1/novels/{id}/chapters/{chapterId}` | GET |
| 保存章节 | `PUT /api/book/{slug}/chapter/{cid}/body` | `PUT /api/v1/novels/{id}/chapters/{chapterId}` | PUT |
| 获取章节结构 | `GET /api/book/{slug}/chapter/{cid}/structure` | `GET /api/v1/novels/{id}/chapters/{chapterId}/structure` | GET |
| 获取章节审稿 | `GET /api/book/{slug}/chapter/{cid}/review` | `GET /api/v1/novels/{id}/chapters/{chapterId}/review` | GET |
| 保存章节审稿 | `PUT /api/book/{slug}/chapter/{cid}/review` | `PUT /api/v1/novels/{id}/chapters/{chapterId}/review` | PUT |
| AI 审稿 | `POST /api/book/{slug}/chapter/{cid}/review-ai` | `POST /api/v1/novels/{id}/chapters/{chapterId}/ai-review` | POST |

#### 设定（Bible）资源

| 功能 | 旧 API | 新 API | HTTP 方法 |
|------|--------|--------|-----------|
| 获取设定 | `GET /api/book/{slug}/bible` | `GET /api/v1/novels/{id}/bible` | GET |
| 保存设定 | `PUT /api/book/{slug}/bible` | `PUT /api/v1/novels/{id}/bible` | PUT |
| 获取人物关系 | `GET /api/book/{slug}/cast` | `GET /api/v1/novels/{id}/bible/characters` | GET |
| 保存人物关系 | `PUT /api/book/{slug}/cast` | `PUT /api/v1/novels/{id}/bible/characters` | PUT |
| 搜索人物 | `GET /api/book/{slug}/cast/search` | `GET /api/v1/novels/{id}/bible/characters/search` | GET |
| 人物覆盖率 | `GET /api/book/{slug}/cast/coverage` | `GET /api/v1/novels/{id}/bible/characters/coverage` | GET |
| 获取知识图谱 | `GET /api/book/{slug}/knowledge` | `GET /api/v1/novels/{id}/bible/knowledge` | GET |
| 保存知识图谱 | `PUT /api/book/{slug}/knowledge` | `PUT /api/v1/novels/{id}/bible/knowledge` | PUT |
| 搜索知识 | `GET /api/book/{slug}/knowledge/search` | `GET /api/v1/novels/{id}/bible/knowledge/search` | GET |

#### 对话（Conversation）资源

| 功能 | 旧 API | 新 API | HTTP 方法 |
|------|--------|--------|-----------|
| 获取消息列表 | `GET /api/book/{slug}/chat/messages` | `GET /api/v1/novels/{id}/conversations/messages` | GET |
| 发送消息 | `POST /api/book/{slug}/chat` | `POST /api/v1/novels/{id}/conversations/messages` | POST |
| 流式聊天 | `POST /api/book/{slug}/chat/stream` | `POST /api/v1/novels/{id}/conversations/stream` | POST |
| 清空对话 | `POST /api/book/{slug}/chat/clear` | `DELETE /api/v1/novels/{id}/conversations/messages` | DELETE |
| 添加事件 | `POST /api/book/{slug}/chat/append_event` | `POST /api/v1/novels/{id}/conversations/events` | POST |
| 摘要对话 | `POST /api/book/{slug}/chat/digest` | `POST /api/v1/novels/{id}/conversations/digest` | POST |

#### 任务（Task）资源

| 功能 | 旧 API | 新 API | HTTP 方法 |
|------|--------|--------|-----------|
| 创建规划任务 | `POST /api/jobs/{slug}/plan` | `POST /api/v1/novels/{id}/tasks/plan` | POST |
| 创建写作任务 | `POST /api/jobs/{slug}/write` | `POST /api/v1/novels/{id}/tasks/write` | POST |
| 创建执行任务 | `POST /api/jobs/{slug}/run` | `POST /api/v1/novels/{id}/tasks/run` | POST |
| 创建导出任务 | `POST /api/jobs/{slug}/export` | `POST /api/v1/novels/{id}/tasks/export` | POST |
| 获取任务状态 | `GET /api/jobs/{job_id}` | `GET /api/v1/tasks/{taskId}` | GET |
| 取消任务 | `POST /api/jobs/{job_id}/cancel` | `DELETE /api/v1/tasks/{taskId}` | DELETE |

#### 统计（Statistics）资源

| 功能 | 旧 API | 新 API | HTTP 方法 |
|------|--------|--------|-----------|
| 全局统计 | `GET /api/stats/global` | `GET /api/v1/statistics/global` | GET |
| 书籍统计 | `GET /api/stats/book/{slug}` | `GET /api/v1/statistics/novels/{id}` | GET |
| 趋势数据 | `GET /api/stats/book/{slug}/trends` | `GET /api/v1/statistics/novels/{id}/trends` | GET |

#### 其他资源

| 功能 | 旧 API | 新 API | HTTP 方法 |
|------|--------|--------|-----------|
| 日志流 | `GET /api/logs/stream` | `GET /api/v1/logs/stream` | GET |

### API 变更说明

**主要变更：**

1. **资源名称** - `book` → `novel`（更准确的领域术语）
2. **标识符** - `slug` → `id`（使用统一的 ID）
3. **资源层级** - 更清晰的嵌套关系（如 `characters` 和 `knowledge` 归入 `bible`）
4. **HTTP 方法** - 使用语义化的 HTTP 方法（DELETE 代替 POST cancel）
5. **版本前缀** - 统一使用 `/api/v1/`

**向后兼容：**
- 本次重构不保留旧 API
- 前端需要同步更新
- 新项目，无历史包袱

---

## 领域模型

### Novel 聚合根

**实体结构：**

```python
# domain/novel/entities/novel.py
class Novel:
    """小说聚合根"""
    id: NovelId
    title: str
    author: str
    stage: NovelStage  # planning, writing, reviewing, completed
    target_chapters: int
    created_at: datetime
    updated_at: datetime

    # 聚合内实体
    chapters: List[Chapter]
    manuscripts: List[Manuscript]

    def add_chapter(self, chapter: Chapter) -> None:
        """添加章节（业务规则：章节号必须连续）"""

    def complete_chapter(self, chapter_id: ChapterId) -> None:
        """完成章节（发布领域事件）"""

    def validate_consistency(self) -> List[ValidationError]:
        """验证小说一致性"""

# domain/novel/entities/chapter.py
class Chapter:
    """章节实体"""
    id: ChapterId
    novel_id: NovelId
    number: int
    title: str
    content: ChapterContent  # 值对象
    word_count: WordCount    # 值对象
    status: ChapterStatus    # draft, reviewing, completed
    scenes: List[Scene]

    def update_content(self, content: str) -> None:
        """更新内容（自动重新计算字数）"""

    def add_scene(self, scene: Scene) -> None:
        """添加场景"""

# domain/novel/value_objects/chapter_content.py
class ChapterContent:
    """章节内容值对象"""
    raw_text: str
    formatted_html: str

    def __init__(self, raw_text: str):
        self.raw_text = raw_text
        self.formatted_html = self._format_to_html(raw_text)

    def _format_to_html(self, text: str) -> str:
        """Markdown 转 HTML"""
```

### Bible 聚合根

**实体结构：**

```python
# domain/bible/entities/bible.py
class Bible:
    """设定聚合根"""
    id: BibleId
    novel_id: NovelId

    # 聚合内实体
    characters: List[Character]
    world_settings: List[WorldSetting]
    knowledge_graph: KnowledgeGraph

    def add_character(self, character: Character) -> None:
        """添加人物"""

    def update_relationship(self, char1_id: CharacterId,
                          char2_id: CharacterId,
                          relationship: str) -> None:
        """更新人物关系"""

    def search_knowledge(self, query: str) -> List[KnowledgeNode]:
        """搜索知识图谱"""

# domain/bible/entities/character.py
class Character:
    """人物实体"""
    id: CharacterId
    name: str
    description: str
    appearance: str
    personality: str
    relationships: Dict[CharacterId, Relationship]
    appearances: List[ChapterAppearance]  # 出场记录

    def add_appearance(self, chapter_id: ChapterId,
                      scene_number: int) -> None:
        """记录出场"""
```

### AI 领域

**实体结构：**

```python
# domain/ai/entities/generation_task.py
class GenerationTask:
    """AI 生成任务聚合根"""
    id: TaskId
    novel_id: NovelId
    task_type: TaskType  # plan, write, review, export
    status: TaskStatus   # pending, running, completed, failed

    prompt: Prompt       # 值对象
    result: GenerationResult
    token_usage: TokenUsage  # 值对象

    created_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]

    def start(self) -> None:
        """开始任务（状态转换）"""

    def complete(self, result: GenerationResult) -> None:
        """完成任务（发布事件）"""

    def fail(self, error: str) -> None:
        """任务失败"""

# domain/ai/services/llm_service.py
class LLMService:
    """LLM 领域服务接口（由基础设施层实现）"""

    @abstractmethod
    async def generate(self, prompt: Prompt,
                      config: GenerationConfig) -> GenerationResult:
        """生成内容"""

    @abstractmethod
    async def stream_generate(self, prompt: Prompt,
                             config: GenerationConfig) -> AsyncIterator[str]:
        """流式生成"""
```

### 领域事件

```python
# domain/shared/events.py
class DomainEvent:
    """领域事件基类"""
    event_id: str
    occurred_at: datetime
    aggregate_id: str

class ChapterCompletedEvent(DomainEvent):
    """章节完成事件"""
    novel_id: NovelId
    chapter_id: ChapterId
    word_count: int

class GenerationTaskCompletedEvent(DomainEvent):
    """生成任务完成事件"""
    task_id: TaskId
    novel_id: NovelId
    token_usage: TokenUsage
```

---

## TDD 测试策略

### 测试金字塔

```
        /\
       /E2E\      10% - 端到端测试
      /------\
     /  集成  \    30% - 集成测试
    /----------\
   /   单元测试  \  60% - 单元测试
  /--------------\
```

**目标覆盖率：**
- 整体覆盖率 > 80%
- 领域层覆盖率 > 90%（核心业务逻辑）
- 应用层覆盖率 > 80%
- 基础设施层覆盖率 > 70%

### 单元测试示例

**领域实体测试：**

```python
# tests/unit/domain/novel/test_novel.py
def test_add_chapter_with_sequential_number():
    """测试添加章节 - 章节号连续"""
    # Arrange
    novel = Novel(id=NovelId("novel-1"), title="测试小说")
    chapter1 = Chapter(number=1, title="第一章")
    chapter2 = Chapter(number=2, title="第二章")

    # Act
    novel.add_chapter(chapter1)
    novel.add_chapter(chapter2)

    # Assert
    assert len(novel.chapters) == 2
    assert novel.chapters[0].number == 1
    assert novel.chapters[1].number == 2

def test_add_chapter_with_non_sequential_number_raises_error():
    """测试添加章节 - 章节号不连续应抛出异常"""
    # Arrange
    novel = Novel(id=NovelId("novel-1"), title="测试小说")
    chapter1 = Chapter(number=1, title="第一章")
    chapter3 = Chapter(number=3, title="第三章")  # 跳过第2章

    # Act & Assert
    novel.add_chapter(chapter1)
    with pytest.raises(InvalidChapterNumberError):
        novel.add_chapter(chapter3)
```

**值对象测试：**

```python
# tests/unit/domain/novel/test_chapter_content.py
def test_chapter_content_formats_markdown_to_html():
    """测试章节内容 - Markdown 转 HTML"""
    # Arrange
    markdown = "# 标题\n\n这是一段**粗体**文字。"

    # Act
    content = ChapterContent(markdown)

    # Assert
    assert "<h1>标题</h1>" in content.formatted_html
    assert "<strong>粗体</strong>" in content.formatted_html

def test_chapter_content_is_immutable():
    """测试章节内容 - 值对象不可变"""
    # Arrange
    content = ChapterContent("原始内容")

    # Act & Assert
    with pytest.raises(AttributeError):
        content.raw_text = "修改内容"  # 应该失败
```

### 集成测试示例

**仓储集成测试：**

```python
# tests/integration/infrastructure/test_file_novel_repository.py
@pytest.fixture
def temp_storage(tmp_path):
    """临时存储目录"""
    return FileStorage(base_path=tmp_path)

def test_save_and_load_novel(temp_storage):
    """测试保存和加载小说"""
    # Arrange
    repo = FileNovelRepository(storage=temp_storage)
    novel = Novel(
        id=NovelId("novel-1"),
        title="测试小说",
        author="测试作者"
    )

    # Act
    repo.save(novel)
    loaded_novel = repo.get_by_id(NovelId("novel-1"))

    # Assert
    assert loaded_novel.id == novel.id
    assert loaded_novel.title == novel.title
    assert loaded_novel.author == novel.author
```

**API 集成测试：**

```python
# tests/integration/interfaces/api/test_novels_api.py
@pytest.fixture
def client():
    """测试客户端"""
    return TestClient(app)

def test_create_novel(client):
    """测试创建小说 API"""
    # Arrange
    payload = {
        "title": "测试小说",
        "author": "测试作者",
        "target_chapters": 10
    }

    # Act
    response = client.post("/api/v1/novels", json=payload)

    # Assert
    assert response.status_code == 201
    data = response.json()
    assert data["success"] is True
    assert data["data"]["title"] == "测试小说"
    assert "id" in data["data"]
```

### E2E 测试示例

```python
# tests/e2e/test_novel_creation_workflow.py
def test_complete_novel_creation_workflow(client):
    """测试完整的小说创建流程"""
    # 1. 创建小说
    novel_response = client.post("/api/v1/novels", json={
        "title": "测试小说",
        "author": "测试作者",
        "target_chapters": 3
    })
    novel_id = novel_response.json()["data"]["id"]

    # 2. 创建设定
    bible_response = client.put(f"/api/v1/novels/{novel_id}/bible", json={
        "world_setting": "现代都市",
        "main_characters": ["主角", "配角A"]
    })
    assert bible_response.status_code == 200

    # 3. 创建规划任务
    plan_response = client.post(f"/api/v1/novels/{novel_id}/tasks/plan", json={
        "chapters": 3
    })
    task_id = plan_response.json()["data"]["task_id"]

    # 4. 等待任务完成
    for _ in range(30):  # 最多等待30秒
        task_response = client.get(f"/api/v1/tasks/{task_id}")
        if task_response.json()["data"]["status"] == "completed":
            break
        time.sleep(1)

    # 5. 验证章节已创建
    chapters_response = client.get(f"/api/v1/novels/{novel_id}/chapters")
    chapters = chapters_response.json()["data"]
    assert len(chapters) == 3
```

### 测试工具和配置

**pytest 配置：**

```ini
# pytest.ini
[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*

# 覆盖率配置
addopts =
    --cov=aitext
    --cov-report=html
    --cov-report=term-missing
    --cov-fail-under=80
    -v

# 标记
markers =
    unit: 单元测试
    integration: 集成测试
    e2e: 端到端测试
    slow: 慢速测试
```

**测试命令：**

```bash
# 运行所有测试
pytest

# 只运行单元测试
pytest -m unit

# 只运行集成测试
pytest -m integration

# 运行特定文件
pytest tests/unit/domain/novel/test_novel.py

# 生成覆盖率报告
pytest --cov=aitext --cov-report=html
```

---

## 旧代码清理

### 清理策略

**原则：**
1. **渐进式迁移** - 新旧代码短期共存，逐步替换
2. **保持可运行** - 每次迁移后系统仍可正常运行
3. **测试先行** - 迁移前为旧代码补充测试
4. **一次一个模块** - 避免大爆炸式重构

### Web 层清理计划

**当前状态：**
- `web/app.py` - 762 行，30+ 路由端点

**迁移步骤：**

**Week 1：创建新架构骨架**

```
web/
├── app.py (保留，逐步清空)
├── routers/
│   ├── __init__.py
│   ├── novels.py (新)
│   ├── chapters.py (新)
│   ├── bible.py (新)
│   ├── tasks.py (新)
│   └── stats.py (新)
├── services/
│   ├── __init__.py
│   ├── novel_service.py (新)
│   └── chapter_service.py (新)
└── repositories/
    ├── __init__.py
    └── novel_repository.py (新)
```

**Week 2：迁移路由（按模块）**

1. **迁移小说路由**
   - 从 `app.py` 提取 `/api/books` 相关路由
   - 移动到 `routers/novels.py`
   - 更新为新 API 格式 `/api/v1/novels`
   - 测试验证
   - 从 `app.py` 删除旧路由

2. **迁移章节路由**
   - 提取 `/api/book/{slug}/chapter` 相关路由
   - 移动到 `routers/chapters.py`
   - 更新为 `/api/v1/novels/{id}/chapters`
   - 测试验证
   - 删除旧路由

3. **迁移设定路由**
   - 提取 `/api/book/{slug}/bible` 等路由
   - 移动到 `routers/bible.py`
   - 更新为 `/api/v1/novels/{id}/bible`
   - 测试验证
   - 删除旧路由

**Week 3：清理和优化**

4. **迁移任务路由**
   - 提取 `/api/jobs` 相关路由
   - 移动到 `routers/tasks.py`
   - 更新为 `/api/v1/tasks`
   - 测试验证
   - 删除旧路由

5. **最终清理**
   - 验证 `app.py` 只剩下应用初始化代码
   - 删除未使用的导入
   - 删除注释掉的旧代码
   - 更新文档

**迁移检查清单：**

```markdown
- [ ] 新路由功能完整
- [ ] 新路由测试通过
- [ ] 前端已更新 API 调用
- [ ] 前端测试通过
- [ ] 旧路由已删除
- [ ] 无未使用的导入
- [ ] 文档已更新
```

### AI 核心模块清理

**当前状态：**
- `clients/llm.py` - 222 行
- `pipeline/runner.py` - 357 行
- `story/engine.py` - 498 行

**迁移步骤：**

**Week 1：创建领域层和基础设施层**

```
domain/
└── ai/
    ├── entities/
    │   └── generation_task.py (新)
    ├── services/
    │   └── llm_service.py (接口，新)
    └── value_objects/
        └── prompt.py (新)

infrastructure/
└── ai/
    ├── llm_client_impl.py (新)
    └── providers/
        ├── anthropic_provider.py (新)
        └── ark_provider.py (新)
```

**Week 2：迁移 LLM 客户端**

1. **提取接口**
   - 从 `clients/llm.py` 分析公共接口
   - 定义 `domain/ai/services/llm_service.py` 接口
   - 实现 `infrastructure/ai/llm_client_impl.py`

2. **迁移提供商**
   - Anthropic 实现 → `providers/anthropic_provider.py`
   - ARK 实现 → `providers/ark_provider.py`
   - 测试验证

3. **替换调用**
   - 更新 `pipeline/runner.py` 使用新接口
   - 更新 `story/engine.py` 使用新接口
   - 测试验证
   - 删除 `clients/llm.py`

**Week 3：重构 Pipeline 和 Story Engine**

4. **重构 Pipeline**
   - 提取领域逻辑到 `domain/novel/services/`
   - 提取应用逻辑到 `application/commands/`
   - 保留编排逻辑在 `pipeline/runner.py`（简化版）
   - 测试验证

5. **重构 Story Engine**
   - 提取章节生成逻辑到 `domain/novel/services/chapter_generation_service.py`
   - 提取一致性检查到 `domain/novel/services/consistency_check_service.py`
   - 简化 `story/engine.py` 为薄层
   - 测试验证

**文件对照表：**

| 旧文件 | 新位置 | 说明 |
|--------|--------|------|
| `clients/llm.py` | `infrastructure/ai/providers/` | 拆分为多个提供商 |
| `pipeline/runner.py` | `application/commands/` + `domain/novel/services/` | 分离编排和业务逻辑 |
| `story/engine.py` | `domain/novel/services/` | 提取领域服务 |

### 删除清单

**Week 3 结束时删除：**

```bash
# 旧的 Web 层代码（已迁移到 routers/）
# app.py 保留但大幅简化

# 旧的 AI 客户端（已迁移到 infrastructure/ai/）
rm clients/llm.py

# 旧的业务逻辑（已迁移到 domain/ 和 application/）
# pipeline/runner.py 保留但简化
# story/engine.py 保留但简化
```

---

## 前端适配

### API 客户端更新

**当前状态：**
- `web-app/src/api/book.ts` - 使用旧 API 格式

**更新策略：**

**1. 创建新的 API 类型定义**

```typescript
// web-app/src/types/api.ts
export interface ApiResponse<T> {
  success: boolean
  data?: T
  error?: {
    code: string
    message: string
    details?: Record<string, any>
  }
  meta: {
    timestamp: string
    version: string
  }
}

export interface Novel {
  id: string
  title: string
  author: string
  stage: 'planning' | 'writing' | 'reviewing' | 'completed'
  target_chapters: number
  completed_chapters: number
  created_at: string
  updated_at: string
}

export interface Chapter {
  id: string
  novel_id: string
  number: number
  title: string
  content: string
  word_count: number
  status: 'draft' | 'reviewing' | 'completed'
}

export interface Bible {
  id: string
  novel_id: string
  world_setting: string
  characters: Character[]
  knowledge_graph: KnowledgeGraph
}
```

**2. 更新 API 客户端**

```typescript
// web-app/src/api/novels.ts (新文件)
import axios from 'axios'
import type { ApiResponse, Novel, Chapter } from '@/types/api'

const API_BASE = '/api/v1'

export const novelsApi = {
  // 获取小说列表
  async list(): Promise<Novel[]> {
    const response = await axios.get<ApiResponse<Novel[]>>(`${API_BASE}/novels`)
    if (!response.data.success) {
      throw new Error(response.data.error?.message || 'Failed to fetch novels')
    }
    return response.data.data!
  },

  // 获取小说详情
  async get(id: string): Promise<Novel> {
    const response = await axios.get<ApiResponse<Novel>>(`${API_BASE}/novels/${id}`)
    if (!response.data.success) {
      throw new Error(response.data.error?.message || 'Failed to fetch novel')
    }
    return response.data.data!
  },

  // 创建小说
  async create(data: Partial<Novel>): Promise<Novel> {
    const response = await axios.post<ApiResponse<Novel>>(`${API_BASE}/novels`, data)
    if (!response.data.success) {
      throw new Error(response.data.error?.message || 'Failed to create novel')
    }
    return response.data.data!
  },

  // 更新小说
  async update(id: string, data: Partial<Novel>): Promise<Novel> {
    const response = await axios.put<ApiResponse<Novel>>(`${API_BASE}/novels/${id}`, data)
    if (!response.data.success) {
      throw new Error(response.data.error?.message || 'Failed to update novel')
    }
    return response.data.data!
  },

  // 删除小说
  async delete(id: string): Promise<void> {
    const response = await axios.delete<ApiResponse<void>>(`${API_BASE}/novels/${id}`)
    if (!response.data.success) {
      throw new Error(response.data.error?.message || 'Failed to delete novel')
    }
  }
}

export const chaptersApi = {
  // 获取章节列表
  async list(novelId: string): Promise<Chapter[]> {
    const response = await axios.get<ApiResponse<Chapter[]>>(
      `${API_BASE}/novels/${novelId}/chapters`
    )
    if (!response.data.success) {
      throw new Error(response.data.error?.message || 'Failed to fetch chapters')
    }
    return response.data.data!
  },

  // 获取章节内容
  async get(novelId: string, chapterId: string): Promise<Chapter> {
    const response = await axios.get<ApiResponse<Chapter>>(
      `${API_BASE}/novels/${novelId}/chapters/${chapterId}`
    )
    if (!response.data.success) {
      throw new Error(response.data.error?.message || 'Failed to fetch chapter')
    }
    return response.data.data!
  },

  // 保存章节
  async update(novelId: string, chapterId: string, content: string): Promise<Chapter> {
    const response = await axios.put<ApiResponse<Chapter>>(
      `${API_BASE}/novels/${novelId}/chapters/${chapterId}`,
      { content }
    )
    if (!response.data.success) {
      throw new Error(response.data.error?.message || 'Failed to update chapter')
    }
    return response.data.data!
  }
}
```

**3. 更新 Pinia Store**

```typescript
// web-app/src/stores/novelStore.ts
import { defineStore } from 'pinia'
import { novelsApi, chaptersApi } from '@/api/novels'
import type { Novel, Chapter } from '@/types/api'

export const useNovelStore = defineStore('novel', {
  state: () => ({
    novels: [] as Novel[],
    currentNovel: null as Novel | null,
    currentChapter: null as Chapter | null,
    loading: false,
    error: null as string | null
  }),

  actions: {
    async fetchNovels() {
      this.loading = true
      this.error = null
      try {
        this.novels = await novelsApi.list()
      } catch (error) {
        this.error = error instanceof Error ? error.message : 'Unknown error'
        throw error
      } finally {
        this.loading = false
      }
    },

    async fetchNovel(id: string) {
      this.loading = true
      this.error = null
      try {
        this.currentNovel = await novelsApi.get(id)
      } catch (error) {
        this.error = error instanceof Error ? error.message : 'Unknown error'
        throw error
      } finally {
        this.loading = false
      }
    },

    async createNovel(data: Partial<Novel>) {
      this.loading = true
      this.error = null
      try {
        const novel = await novelsApi.create(data)
        this.novels.push(novel)
        return novel
      } catch (error) {
        this.error = error instanceof Error ? error.message : 'Unknown error'
        throw error
      } finally {
        this.loading = false
      }
    }
  }
})
```

### 组件更新

**需要更新的组件：**

1. **Home.vue** - 书籍列表
   - 更新 API 调用：`/api/books` → `novelsApi.list()`
   - 更新数据结构：`slug` → `id`

2. **Workbench.vue** - 工作台
   - 更新路由参数：`:slug` → `:id`
   - 更新 API 调用：使用新的 `novelsApi` 和 `chaptersApi`
   - 更新数据结构

3. **Chapter.vue** - 章节编辑
   - 更新 API 调用：`/api/book/{slug}/chapter/{cid}/body` → `chaptersApi.update()`
   - 更新保存逻辑

4. **Cast.vue** - 人物关系
   - 更新 API 调用：`/api/book/{slug}/cast` → `/api/v1/novels/{id}/bible/characters`

5. **Knowledge.vue** - 知识图谱
   - 更新 API 调用：`/api/book/{slug}/knowledge` → `/api/v1/novels/{id}/bible/knowledge`

### 路由更新

```typescript
// web-app/src/router/index.ts
const routes = [
  {
    path: '/',
    name: 'Home',
    component: () => import('@/views/Home.vue')
  },
  {
    path: '/novel/:id',  // 从 /book/:slug 改为 /novel/:id
    name: 'Workbench',
    component: () => import('@/views/Workbench.vue'),
    children: [
      {
        path: 'chapter/:chapterId',  // 从 :cid 改为 :chapterId
        name: 'Chapter',
        component: () => import('@/views/Chapter.vue')
      }
    ]
  }
]
```

### 迁移检查清单

```markdown
**API 层：**
- [ ] 创建 `types/api.ts` 类型定义
- [ ] 创建 `api/novels.ts` 新 API 客户端
- [ ] 创建 `api/chapters.ts` 章节 API
- [ ] 创建 `api/bible.ts` 设定 API
- [ ] 创建 `api/tasks.ts` 任务 API
- [ ] 删除旧的 `api/book.ts`

**Store 层：**
- [ ] 更新 `stores/novelStore.ts` 使用新 API
- [ ] 更新 `stores/chapterStore.ts` 使用新 API
- [ ] 测试 Store 功能

**组件层：**
- [ ] 更新 `Home.vue` 书籍列表
- [ ] 更新 `Workbench.vue` 工作台
- [ ] 更新 `Chapter.vue` 章节编辑
- [ ] 更新 `Cast.vue` 人物关系
- [ ] 更新 `Knowledge.vue` 知识图谱
- [ ] 更新所有子组件

**路由层：**
- [ ] 更新路由定义 `slug` → `id`
- [ ] 更新路由守卫
- [ ] 测试路由跳转

**测试：**
- [ ] 端到端测试通过
- [ ] 所有功能正常
- [ ] 无控制台错误
```

---

## 实施路线图

### 总体时间线

**3 周并行开发：Web 层 + AI 核心模块同步重构**

```
Week 1: 基础设施搭建
├─ 后端：创建 DDD 分层结构
├─ 后端：实现领域模型和仓储接口
├─ 后端：实现 AI 领域服务接口
├─ 前端：创建类型定义
└─ 前端：更新 API 客户端

Week 2: 核心功能迁移
├─ 后端：迁移小说和章节路由
├─ 后端：迁移 LLM 客户端
├─ 后端：实现新 API 端点
├─ 前端：更新组件使用新 API
└─ 前端：更新路由

Week 3: 优化和清理
├─ 后端：重构 Pipeline 和 Story Engine
├─ 后端：清理旧代码
├─ 前端：完成所有组件迁移
├─ 测试：集成测试和 E2E 测试
└─ 文档：更新 API 文档
```

### Week 1：基础设施搭建（Day 1-7）

#### Day 1-2：后端 - 创建 DDD 分层结构

**目标：** 搭建完整的目录结构和基础类

**任务清单：**

```bash
# Day 1 上午：创建目录结构
- [ ] 创建 domain/ 目录及子目录
  - domain/novel/entities/
  - domain/novel/value_objects/
  - domain/novel/services/
  - domain/novel/repositories/
  - domain/bible/entities/
  - domain/bible/repositories/
  - domain/ai/entities/
  - domain/ai/services/
  - domain/shared/

- [ ] 创建 application/ 目录及子目录
  - application/commands/
  - application/queries/
  - application/services/
  - application/dto/

- [ ] 创建 infrastructure/ 目录及子目录
  - infrastructure/persistence/repositories/
  - infrastructure/persistence/storage/
  - infrastructure/persistence/mappers/
  - infrastructure/ai/providers/
  - infrastructure/messaging/
  - infrastructure/config/

- [ ] 创建 interfaces/ 目录及子目录
  - interfaces/api/v1/
  - interfaces/api/dependencies.py
  - interfaces/api/middleware/

# Day 1 下午：实现基础类
- [ ] 实现 domain/shared/events.py（领域事件基类）
- [ ] 实现 domain/shared/exceptions.py（领域异常）
- [ ] 实现 infrastructure/config/settings.py（配置管理）

# Day 2 上午：实现值对象
- [ ] 实现 domain/novel/value_objects/novel_id.py
- [ ] 实现 domain/novel/value_objects/chapter_content.py
- [ ] 实现 domain/novel/value_objects/word_count.py
- [ ] 实现 domain/ai/value_objects/prompt.py
- [ ] 实现 domain/ai/value_objects/token_usage.py

# Day 2 下午：编写单元测试
- [ ] 测试值对象的不可变性
- [ ] 测试值对象的验证逻辑
- [ ] 测试覆盖率 > 90%
```

#### Day 3-4：后端 - 实现领域实体和仓储接口

**目标：** 完成核心领域模型

**任务清单：**

```bash
# Day 3 上午：实现 Novel 聚合根
- [ ] 实现 domain/novel/entities/novel.py
  - Novel 实体类
  - add_chapter() 方法
  - complete_chapter() 方法
  - validate_consistency() 方法

- [ ] 实现 domain/novel/entities/chapter.py
  - Chapter 实体类
  - update_content() 方法
  - add_scene() 方法

- [ ] 实现 domain/novel/entities/manuscript.py

# Day 3 下午：实现 Bible 聚合根
- [ ] 实现 domain/bible/entities/bible.py
  - Bible 实体类
  - add_character() 方法
  - update_relationship() 方法
  - search_knowledge() 方法

- [ ] 实现 domain/bible/entities/character.py
- [ ] 实现 domain/bible/entities/world_setting.py

# Day 4 上午：实现 AI 领域
- [ ] 实现 domain/ai/entities/generation_task.py
  - GenerationTask 实体类
  - start() 方法
  - complete() 方法
  - fail() 方法

- [ ] 实现 domain/ai/services/llm_service.py（接口）
- [ ] 实现 domain/ai/services/prompt_builder.py

# Day 4 下午：实现仓储接口
- [ ] 实现 domain/novel/repositories/novel_repository.py（接口）
- [ ] 实现 domain/novel/repositories/chapter_repository.py（接口）
- [ ] 实现 domain/bible/repositories/bible_repository.py（接口）
- [ ] 实现 domain/ai/repositories/conversation_repository.py（接口）

# Day 4 晚上：编写单元测试
- [ ] 测试实体的业务逻辑
- [ ] 测试聚合根的一致性规则
- [ ] 测试覆盖率 > 90%
```

#### Day 5-6：后端 - 实现基础设施层

**目标：** 实现仓储和存储抽象

**任务清单：**

```bash
# Day 5 上午：实现存储抽象
- [ ] 实现 infrastructure/persistence/storage/storage_backend.py（接口）
- [ ] 实现 infrastructure/persistence/storage/file_storage.py
  - read() 方法
  - write() 方法
  - exists() 方法
  - delete() 方法

# Day 5 下午：实现仓储实现
- [ ] 实现 infrastructure/persistence/repositories/file_novel_repository.py
  - save() 方法
  - get_by_id() 方法
  - list_all() 方法
  - delete() 方法

- [ ] 实现 infrastructure/persistence/mappers/novel_mapper.py
  - to_dict() 方法
  - from_dict() 方法

# Day 6 上午：实现 AI 基础设施
- [ ] 实现 infrastructure/ai/llm_client_impl.py
- [ ] 实现 infrastructure/ai/providers/anthropic_provider.py
  - generate() 方法
  - stream_generate() 方法

- [ ] 实现 infrastructure/ai/providers/ark_provider.py

# Day 6 下午：编写集成测试
- [ ] 测试文件存储读写
- [ ] 测试仓储保存和加载
- [ ] 测试 LLM 客户端调用（使用 mock）
- [ ] 测试覆盖率 > 70%
```

#### Day 7：前端 - 类型定义和 API 客户端

**目标：** 创建前端基础设施

**任务清单：**

```bash
# Day 7 上午：创建类型定义
- [ ] 创建 web-app/src/types/api.ts
  - ApiResponse<T> 接口
  - Novel 接口
  - Chapter 接口
  - Bible 接口
  - Character 接口
  - GenerationTask 接口

# Day 7 下午：创建 API 客户端
- [ ] 创建 web-app/src/api/novels.ts
  - list() 方法
  - get() 方法
  - create() 方法
  - update() 方法
  - delete() 方法

- [ ] 创建 web-app/src/api/chapters.ts
  - list() 方法
  - get() 方法
  - update() 方法

- [ ] 创建 web-app/src/api/bible.ts
- [ ] 创建 web-app/src/api/tasks.ts

# Day 7 晚上：更新 Store
- [ ] 更新 web-app/src/stores/novelStore.ts 使用新 API
- [ ] 更新 web-app/src/stores/chapterStore.ts 使用新 API
```

### Week 2：核心功能迁移（Day 8-14）

#### Day 8-9：后端 - 迁移小说路由

**目标：** 实现小说相关的新 API

**任务清单：**

```bash
# Day 8 上午：创建应用服务
- [ ] 实现 application/services/novel_service.py
  - create_novel() 方法
  - get_novel() 方法
  - list_novels() 方法
  - update_novel() 方法
  - delete_novel() 方法

- [ ] 实现 application/dto/novel_dto.py

# Day 8 下午：创建路由
- [ ] 实现 interfaces/api/v1/novels.py
  - POST /api/v1/novels
  - GET /api/v1/novels
  - GET /api/v1/novels/{id}
  - PUT /api/v1/novels/{id}
  - DELETE /api/v1/novels/{id}

- [ ] 实现依赖注入 interfaces/api/dependencies.py

# Day 9 上午：编写测试
- [ ] 单元测试：测试 novel_service.py
- [ ] 集成测试：测试 novels.py 路由
- [ ] 测试覆盖率 > 80%

# Day 9 下午：迁移旧代码
- [ ] 从 web/app.py 删除旧的 /api/books 路由
- [ ] 验证新 API 功能完整
- [ ] 回归测试
```

#### Day 10-11：后端 - 迁移章节路由

**目标：** 实现章节相关的新 API

**任务清单：**

```bash
# Day 10 上午：创建应用服务
- [ ] 实现 application/services/chapter_service.py
  - get_chapter() 方法
  - list_chapters() 方法
  - update_chapter_content() 方法
  - get_chapter_structure() 方法
  - get_chapter_review() 方法
  - update_chapter_review() 方法

# Day 10 下午：创建路由
- [ ] 实现 interfaces/api/v1/chapters.py
  - GET /api/v1/novels/{id}/chapters
  - GET /api/v1/novels/{id}/chapters/{chapterId}
  - PUT /api/v1/novels/{id}/chapters/{chapterId}
  - GET /api/v1/novels/{id}/chapters/{chapterId}/structure
  - GET /api/v1/novels/{id}/chapters/{chapterId}/review
  - PUT /api/v1/novels/{id}/chapters/{chapterId}/review
  - POST /api/v1/novels/{id}/chapters/{chapterId}/ai-review

# Day 11 上午：编写测试
- [ ] 单元测试：测试 chapter_service.py
- [ ] 集成测试：测试 chapters.py 路由
- [ ] 测试覆盖率 > 80%

# Day 11 下午：迁移旧代码
- [ ] 从 web/app.py 删除旧的章节路由
- [ ] 验证新 API 功能完整
- [ ] 回归测试
```

#### Day 12-13：后端 - 迁移 LLM 客户端

**目标：** 重构 AI 核心模块

**任务清单：**

```bash
# Day 12 上午：分析旧代码
- [ ] 分析 clients/llm.py 的公共接口
- [ ] 识别 Anthropic 和 ARK 的差异
- [ ] 设计统一的提供商接口

# Day 12 下午：实现提供商
- [ ] 完善 infrastructure/ai/providers/anthropic_provider.py
  - 实现完整的 generate() 方法
  - 实现 stream_generate() 方法
  - 错误处理和重试逻辑

- [ ] 完善 infrastructure/ai/providers/ark_provider.py
  - 实现相同的接口
  - 适配 ARK API 格式

# Day 13 上午：更新调用方
- [ ] 更新 pipeline/runner.py 使用新的 LLM 服务
- [ ] 更新 story/engine.py 使用新的 LLM 服务
- [ ] 测试验证

# Day 13 下午：清理旧代码
- [ ] 删除 clients/llm.py
- [ ] 更新导入语句
- [ ] 回归测试
```

#### Day 14：前端 - 更新核心组件

**目标：** 更新主要组件使用新 API

**任务清单：**

```bash
# Day 14 上午：更新 Home.vue
- [ ] 使用 novelsApi.list() 获取书籍列表
- [ ] 更新数据结构 slug → id
- [ ] 更新路由跳转 /book/:slug → /novel/:id
- [ ] 测试验证

# Day 14 下午：更新 Workbench.vue
- [ ] 更新路由参数 :slug → :id
- [ ] 使用 novelsApi.get() 获取小说详情
- [ ] 使用 chaptersApi.list() 获取章节列表
- [ ] 测试验证

# Day 14 晚上：更新路由
- [ ] 更新 router/index.ts 路由定义
- [ ] 测试路由跳转
- [ ] 测试浏览器前进后退
```

### Week 3：优化和清理（Day 15-21）

#### Day 15-16：后端 - 重构 Pipeline 和 Story Engine

**目标：** 提取领域逻辑，简化编排层

**任务清单：**

```bash
# Day 15 上午：提取领域服务
- [ ] 实现 domain/novel/services/chapter_generation_service.py
  - generate_chapter_outline() 方法
  - generate_chapter_content() 方法
  - validate_chapter_consistency() 方法

- [ ] 实现 domain/novel/services/consistency_check_service.py
  - check_character_consistency() 方法
  - check_timeline_consistency() 方法
  - check_setting_consistency() 方法

# Day 15 下午：提取应用命令
- [ ] 实现 application/commands/create_novel.py
- [ ] 实现 application/commands/write_chapter.py
- [ ] 实现 application/commands/generate_with_ai.py

# Day 16 上午：简化 Pipeline
- [ ] 重构 pipeline/runner.py
  - 移除业务逻辑
  - 只保留编排逻辑
  - 调用应用层命令

- [ ] 重构 story/engine.py
  - 移除业务逻辑
  - 调用领域服务

# Day 16 下午：编写测试
- [ ] 测试领域服务
- [ ] 测试应用命令
- [ ] 测试 Pipeline 编排
- [ ] 测试覆盖率 > 80%
```

#### Day 17-18：前端 - 完成组件迁移

**目标：** 更新所有剩余组件

**任务清单：**

```bash
# Day 17 上午：更新 Chapter.vue
- [ ] 使用 chaptersApi.get() 获取章节内容
- [ ] 使用 chaptersApi.update() 保存章节
- [ ] 更新路由参数 :cid → :chapterId
- [ ] 测试验证

# Day 17 下午：更新 Cast.vue
- [ ] 使用新 API /api/v1/novels/{id}/bible/characters
- [ ] 更新数据结构
- [ ] 测试验证

# Day 18 上午：更新 Knowledge.vue
- [ ] 使用新 API /api/v1/novels/{id}/bible/knowledge
- [ ] 更新数据结构
- [ ] 测试验证

# Day 18 下午：更新其他组件
- [ ] 更新所有子组件
- [ ] 删除旧的 api/book.ts
- [ ] 清理未使用的代码
```

#### Day 19-20：测试和优化

**目标：** 全面测试和性能优化

**任务清单：**

```bash
# Day 19 上午：后端测试
- [ ] 运行所有单元测试
- [ ] 运行所有集成测试
- [ ] 运行 E2E 测试
- [ ] 修复失败的测试

# Day 19 下午：前端测试
- [ ] 端到端测试所有功能
- [ ] 测试创建小说流程
- [ ] 测试章节编辑流程
- [ ] 测试 AI 生成流程

# Day 20 上午：性能优化
- [ ] 后端：添加缓存
- [ ] 后端：优化数据库查询
- [ ] 前端：优化 API 调用（并行化）
- [ ] 前端：添加加载状态

# Day 20 下午：代码审查
- [ ] 审查代码质量
- [ ] 检查测试覆盖率
- [ ] 修复代码异味
- [ ] 更新注释和文档
```

#### Day 21：文档和发布

**目标：** 完成文档，准备发布

**任务清单：**

```bash
# Day 21 上午：更新文档
- [ ] 更新 API 文档
- [ ] 更新架构文档
- [ ] 更新开发指南
- [ ] 更新部署文档

# Day 21 下午：最终检查
- [ ] 运行完整测试套件
- [ ] 检查所有功能
- [ ] 验证性能指标
- [ ] 准备发布说明

# Day 21 晚上：发布
- [ ] 创建 Git tag
- [ ] 合并到主分支
- [ ] 部署到生产环境
- [ ] 监控系统运行
```

---

## 风险管理

### 技术风险

#### 风险 1：领域模型设计不合理

**描述：** DDD 聚合根边界划分不当，导致性能问题或一致性问题

**影响：** 高
**概率：** 中

**缓解措施：**
- 在 Week 1 Day 3-4 完成领域模型后，进行设计评审
- 编写单元测试验证聚合根的一致性规则
- 如果发现问题，及时调整边界
- 参考 DDD 最佳实践和案例

**应急计划：**
- 如果聚合根设计有严重问题，回退到简单的分层架构
- 保留领域层和应用层分离，但简化聚合根逻辑

#### 风险 2：仓储抽象层性能问题

**描述：** 抽象存储层增加了额外的开销，影响性能

**影响：** 中
**概率：** 低

**缓解措施：**
- 在 Week 1 Day 6 进行性能基准测试
- 对比新旧实现的性能差异
- 如果性能下降 > 20%，优化实现
- 添加缓存层减少 I/O 操作

**应急计划：**
- 如果性能问题无法解决，简化抽象层
- 直接使用文件存储，保留接口以便未来扩展

#### 风险 3：LLM 客户端迁移失败

**描述：** 新的 LLM 客户端实现与旧版本行为不一致

**影响：** 高
**概率：** 中

**缓解措施：**
- 在 Week 2 Day 12 详细分析旧代码行为
- 编写集成测试对比新旧实现的输出
- 使用相同的测试用例验证一致性
- 保留旧代码作为参考

**应急计划：**
- 如果新实现有问题，暂时保留旧代码
- 使用适配器模式包装旧实现
- 逐步迁移，而不是一次性替换

### 进度风险

#### 风险 4：开发时间超出预期

**描述：** 3 周时间不够完成所有任务

**影响：** 高
**概率：** 中

**缓解措施：**
- 采用 MVP 优先策略，先实现核心功能
- 每周进行进度评估和调整
- 识别可以延后的功能
- 前后端并行开发，提高效率

**应急计划：**
- 如果 Week 2 结束时进度落后 > 30%，调整范围
- 优先完成 Web 层重构，AI 模块重构延后
- 或者优先完成新 API，旧代码清理延后

#### 风险 5：前后端协调问题

**描述：** 前后端开发进度不同步，导致等待

**影响：** 中
**概率：** 中

**缓解措施：**
- Week 1 Day 1 提前定义好 API 接口
- 前端可以先用 Mock 数据开发
- 每日同步进度，及时调整
- 使用 API 文档工具（如 Swagger）

**应急计划：**
- 如果后端延迟，前端继续使用 Mock 数据
- 如果前端延迟，后端先完成 API 测试

### 质量风险

#### 风险 6：测试覆盖率不足

**描述：** 重构过程中测试覆盖率低于目标（80%）

**影响：** 高
**概率：** 中

**缓解措施：**
- 采用 TDD 方法，先写测试再写代码
- 每天检查测试覆盖率
- 如果覆盖率 < 80%，补充测试
- 代码审查时检查测试质量

**应急计划：**
- 如果时间不够，降低覆盖率目标到 70%
- 优先测试核心业务逻辑（领域层）
- 基础设施层测试可以延后

#### 风险 7：引入新的 Bug

**描述：** 重构过程中引入新的 Bug，影响现有功能

**影响：** 高
**概率：** 高

**缓解措施：**
- 渐进式迁移，保持系统可运行
- 每次迁移后进行回归测试
- 使用 E2E 测试验证关键流程
- 保留旧代码作为备份

**应急计划：**
- 如果发现严重 Bug，立即回滚
- 修复 Bug 后再继续迁移
- 增加测试用例覆盖 Bug 场景

### 成功标准

**Week 1 结束时：**
- [ ] DDD 分层结构完整
- [ ] 领域模型实现完成
- [ ] 基础设施层实现完成
- [ ] 前端类型定义和 API 客户端完成
- [ ] 单元测试覆盖率 > 80%

**Week 2 结束时：**
- [ ] 小说和章节 API 迁移完成
- [ ] LLM 客户端迁移完成
- [ ] 前端核心组件更新完成
- [ ] 集成测试通过
- [ ] 系统可正常运行

**Week 3 结束时：**
- [ ] Pipeline 和 Story Engine 重构完成
- [ ] 所有组件迁移完成
- [ ] 旧代码清理完成
- [ ] 测试覆盖率 > 80%
- [ ] E2E 测试通过
- [ ] 文档更新完成
- [ ] 系统性能满足要求

---

**文档结束**
