# PlotPilot 学习文档

## 项目概述

PlotPilot（墨枢）是一个 AI 驱动的长篇创作平台，提供自动驾驶生成、知识图谱管理、风格分析等一体化功能。

### 核心特性
- **自动驾驶模式**：后台守护进程持续生成章节，支持 SSE 实时流式推送
- **Story Bible**：人物、地点、世界设定的结构化管理
- **知识图谱**：自动提取故事三元组，语义检索历史内容
- **伏笔台账**：追踪并自动闭合叙事钩子
- **风格分析**：作者声音漂移检测与文体指纹
- **节拍表 & 故事结构**：三幕式、章节节拍规划

## 技术架构

### DDD 四层架构

```
PlotPilot/
├── domain/          # 领域层：实体、值对象、仓储接口
│   ├── novel/       # 小说、章节、情节弧
│   ├── bible/       # 人物、地点、世界设定
│   ├── cast/        # 角色关系图
│   ├── knowledge/   # 知识三元组
│   └── shared/      # 基础实体、异常、领域事件
│
├── application/     # 应用层：用例编排、工作流、DTO
│   ├── engine/      # 生成引擎、自动驾驶守护进程
│   ├── analyst/     # 声音分析、张力分析、状态机
│   ├── audit/       # 章节审查、宏观重构
│   └── blueprint/   # 节拍表、故事结构规划
│
├── infrastructure/  # 基础设施层：技术实现
│   ├── ai/          # Anthropic / Ark 提供商、ChromaDB、Qdrant
│   └── persistence/ # SQLite 仓储、Schema 迁移
│
└── interfaces/      # 接口层：FastAPI 路由
    └── api/v1/      # REST API（core / world / engine / audit / analyst）
```

## 快速开始

### 环境要求
- Python 3.9+
- Node.js 18+
- （可选）Docker — 用于启动 Qdrant 向量数据库

### 启动步骤

1. **克隆仓库**
```bash
git clone https://github.com/shenminglinyi/PlotPilot.git
cd PlotPilot
```

2. **后端配置**
```bash
# 创建虚拟环境（推荐）
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt

# 配置环境变量
cp .env.example .env
# 编辑 .env，至少填写以下任一 LLM 凭证：
#   ANTHROPIC_API_KEY   — 使用 Claude 模型
#   ARK_API_KEY         — 使用 ByteDance Doubao 模型
```

3. **启动向量数据库（可选）**
```bash
docker compose up -d
# Qdrant 将运行在 http://localhost:6333
```

4. **下载嵌入模型**
```bash
python scripts/utils/download_embedding_model.py
# 或通过 ModelScope 镜像下载（国内推荐）：
python scripts/utils/download_model_via_modelscope.py
```

5. **启动后端**
```bash
uvicorn interfaces.main:app --host 127.0.0.1 --port 8005 --reload
```
后端 API：http://localhost:8005  
交互文档：http://localhost:8005/docs

6. **启动前端**
```bash
cd frontend
npm install
npm run dev
# 前端运行在 http://localhost:3000
```

## 核心概念

### 1. 自动驾驶守护进程 (AutopilotDaemon)

负责持续监控和生成章节的核心组件：

- **主循环**：每10秒轮询一次活跃小说
- **状态管理**：跟踪每个小说的 current_stage 和 autopilot_status
- **事务最小化**：只在必要时刻写入数据库
- **熔断保护**：防止 API 雪崩

关键文件：
- `application/engine/services/autopilot_daemon.py`
- `scripts/start_daemon.py`

### 2. 自动生成工作流 (AutoNovelGenerationWorkflow)

章节生成的核心流程：

```python
async def generate_chapter_stream():
    # 1. 构建上下文
    context = context_builder.build_structured_context()
    # 2. LLM 生成内容
    content = await llm_service.generate(prompt)
    # 3. 后处理
    chapter_state = await extract_chapter_state(content)
    # 4. 更新状态
    state_updater.update_from_chapter(novel_id, chapter_number, chapter_state)
```

关键集成点：
- `StateUpdater` 集成（待修复）
- `ChapterStateExtractor` 实现（待完成）
- `chapter_elements` 表写入（待完善）

### 3. Story Bible

世界观设定的结构化管理系统：

#### 实体类型
- **Character**：人物，包含关系网络
- **Location**：地点，包含属性信息
- **WorldSetting**：世界设定
- **TimelineNote**：时间线笔记
- **StyleNote**：风格笔记

#### 关系管理
通过 `bible_character_relationships` 表维护角色间复杂关系。

### 4. 知识图谱

基于三元组的知识管理系统：

#### 数据模型
```sql
triples (
    id TEXT PRIMARY KEY,
    subject TEXT,     -- 主体
    predicate TEXT,   -- 谓词
    object TEXT,      -- 客体
    entity_type TEXT, -- 实体类型
    confidence REAL,  -- 置信度
    source TEXT       -- 来源
)
```

#### 应用场景
- 智能检索：语义理解查询
- 关系推理：自动发现隐藏关联
- 上下文构建：为 LLM 提供结构化背景

### 5. 伏笔系统

叙事钩子的追踪和管理：

#### 数据结构
```json
{
  "id": "fr-novel-xxx",
  "planted_in_chapter": 1,
  "description": "伏笔描述",
  "importance": 3,
  "status": "planted|resolved",
  "suggested_resolve_chapter": 5,
  "resolved_in_chapter": null
}
```

#### 自动化流程
- 自动识别潜在伏笔
- 建议闭合时机
- 追踪解决进度

## 数据库设计要点

### 核心表结构

#### story_nodes (故事节点)
存储小说结构层次（part/volume/act/chapter）：
- `node_type`: 节点类型
- `parent_id`: 父节点引用
- `chapter_start/end`: 章节范围
- `planning_status`: 规划状态

#### chapter_elements (章节元素)
关联章节与世界观元素：
- `element_type`: character/location/item/organization/event
- `relation_type`: appears/mentioned/scene/uses/involved/occurs
- `importance`: major/normal/minor

#### triples (知识三元组)
知识图谱核心数据存储。

## 开发指南

### 添加新功能

1. **定义领域模型**（Domain Layer）
   - 创建实体和值对象
   - 定义仓储接口

2. **实现应用服务**（Application Layer）
   - 编写用例逻辑
   - 集成 AI 服务

3. **实现基础设施**（Infrastructure Layer）
   - 数据库仓储实现
   - AI 提供商适配

4. **暴露 API**（Interfaces Layer）
   - FastAPI 路由
   - 请求/响应 DTO

### 测试策略

#### 单元测试
```python
# tests/unit/domain/bible/test_character.py
def test_character_add_relationship():
    character.add_relationship("与李四是好友")
    assert len(character.relationships) == 1
```

#### 集成测试
```python
# tests/integration/
# 测试完整的数据流和业务流程
```

### 代码规范

- **命名约定**：
  - 实体类：PascalCase（如 `Bible`）
  - 服务类：PascalCase（如 `VoiceFingerprintService`）
  - 方法名：camelCase
  - 变量名：snake_case

- **错误处理**：
  - 使用 `domain.shared.exceptions`
  - 区分业务异常和系统异常

- **日志记录**：
  - 使用标准 logging 模块
  - 按模块组织 logger 名称

## 常见问题排查

### 1. 守护进程不工作

检查点：
- ✅ 数据库连接正常
- ✅ `autopilot_status=running` 的小说存在
- ✅ LLM API 密钥有效
- ✅ 日志文件可写

### 2. 章节生成失败

可能原因：
- API 限流（查看熔断器状态）
- 上下文超出 token 限制
- 生成内容不符合一致性检查

### 3. 知识图谱为空

解决方案：
- 确保 `auto_knowledge_generator` 已调用
- 检查三元组数据写入逻辑
- 验证嵌入模型加载成功

## 性能优化

### 数据库优化
- 为常用查询字段建立索引
- 定期清理过期数据
- 使用连接池管理数据库连接

### AI 服务优化
- 缓存频繁使用的上下文
- 批量处理请求减少 API 调用
- 合理设置温度参数平衡创造性和一致性

### 内存管理
- 及时释放大模型加载的显存
- 限制同时运行的生成任务数
- 使用流式处理避免内存溢出

## 部署注意事项

### 生产环境配置
```bash
# 禁用热重载
export PYTHONUNBUFFERED=1

# 设置日志级别
export LOG_LEVEL=WARNING

# 限制并发请求
export UVICORN_WORKERS=4
```

### 监控指标
- 请求延迟（P95 < 2s）
- 错误率（< 1%）
- 守护进程健康状态
- LLM API 调用成功率

## 扩展开发

### 添加新的 AI 提供商
1. 实现 `domain.ai.providers` 中的 Provider 接口
2. 注册到工厂函数
3. 更新环境变量配置

### 支持新的故事结构
1. 扩展 `story_nodes` 表结构
2. 实现对应的规划服务
3. 更新前端展示组件

## 贡献指南

1. Fork 项目
2. 创建特性分支：`git checkout -b feat/your-feature`
3. 提交更改：遵循 [Conventional Commits](https://www.conventionalcommits.org/)
4. 推送并创建 Pull Request

---

**最后更新**: $(date +"%Y-%m-%d %H:%M:%S")