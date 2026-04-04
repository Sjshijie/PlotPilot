-- SQLite Schema for AiText Novel Generation System

-- 小说表
CREATE TABLE IF NOT EXISTS novels (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    slug TEXT UNIQUE NOT NULL,
    target_chapters INTEGER NOT NULL DEFAULT 0,
    premise TEXT DEFAULT '',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 章节表
CREATE TABLE IF NOT EXISTS chapters (
    id TEXT PRIMARY KEY,
    novel_id TEXT NOT NULL,
    number INTEGER NOT NULL,
    title TEXT,
    content TEXT,
    outline TEXT,
    status TEXT DEFAULT 'draft',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (novel_id) REFERENCES novels(id) ON DELETE CASCADE,
    UNIQUE(novel_id, number)
);

-- 人物表
CREATE TABLE IF NOT EXISTS characters (
    id TEXT PRIMARY KEY,
    novel_id TEXT NOT NULL,
    name TEXT NOT NULL,
    role TEXT,  -- 主角/配角/反派/导师
    description TEXT,
    importance TEXT DEFAULT 'normal',  -- high/normal/low
    metadata TEXT,  -- JSON 格式存储额外信息
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (novel_id) REFERENCES novels(id) ON DELETE CASCADE
);

-- 三元组表（知识图谱）
CREATE TABLE IF NOT EXISTS triples (
    id TEXT PRIMARY KEY,
    novel_id TEXT NOT NULL,
    subject TEXT NOT NULL,
    predicate TEXT NOT NULL,
    object TEXT NOT NULL,
    chapter_id TEXT,
    note TEXT,
    entity_type TEXT,  -- 'character' | 'location' | NULL (通用)
    importance TEXT,  -- 人物: 'primary'|'secondary'|'minor', 地点: 'core'|'important'|'normal'
    location_type TEXT,  -- 地点类型: 'city'|'region'|'building'|'faction'|'realm'
    description TEXT,  -- 实体描述
    first_appearance TEXT,  -- 首次出现章节
    related_chapters TEXT,  -- 相关章节列表 (JSON)
    tags TEXT,  -- 标签 (JSON)
    attributes TEXT,  -- 其他属性 (JSON)
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (novel_id) REFERENCES novels(id) ON DELETE CASCADE,
    FOREIGN KEY (chapter_id) REFERENCES chapters(id) ON DELETE SET NULL
);

-- 事件表（时间线）
CREATE TABLE IF NOT EXISTS events (
    id TEXT PRIMARY KEY,
    novel_id TEXT NOT NULL,
    chapter_id TEXT,
    chapter_number INTEGER NOT NULL,
    event_type TEXT NOT NULL,  -- character_introduction/relationship_change/conflict/revelation/decision
    description TEXT NOT NULL,
    story_time TEXT,  -- 故事时间（如"第3天"、"两年后"）
    importance TEXT DEFAULT 'normal',  -- high/normal/low
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (novel_id) REFERENCES novels(id) ON DELETE CASCADE,
    FOREIGN KEY (chapter_id) REFERENCES chapters(id) ON DELETE SET NULL
);

-- 事件-人物关联表
CREATE TABLE IF NOT EXISTS event_characters (
    event_id TEXT NOT NULL,
    character_id TEXT NOT NULL,
    PRIMARY KEY (event_id, character_id),
    FOREIGN KEY (event_id) REFERENCES events(id) ON DELETE CASCADE,
    FOREIGN KEY (character_id) REFERENCES characters(id) ON DELETE CASCADE
);

-- Bible 表（作品设定）
CREATE TABLE IF NOT EXISTS bibles (
    id TEXT PRIMARY KEY,
    novel_id TEXT UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (novel_id) REFERENCES novels(id) ON DELETE CASCADE
);

-- 地点表
CREATE TABLE IF NOT EXISTS locations (
    id TEXT PRIMARY KEY,
    bible_id TEXT NOT NULL,
    name TEXT NOT NULL,
    location_type TEXT,  -- 城市/建筑/区域
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (bible_id) REFERENCES bibles(id) ON DELETE CASCADE
);

-- 时间线笔记表
CREATE TABLE IF NOT EXISTS timeline_notes (
    id TEXT PRIMARY KEY,
    bible_id TEXT NOT NULL,
    content TEXT NOT NULL,
    order_index INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (bible_id) REFERENCES bibles(id) ON DELETE CASCADE
);

-- 风格笔记表
CREATE TABLE IF NOT EXISTS style_notes (
    id TEXT PRIMARY KEY,
    bible_id TEXT NOT NULL,
    category TEXT NOT NULL,
    content TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (bible_id) REFERENCES bibles(id) ON DELETE CASCADE
);

-- 知识表（novel_knowledge.json 的结构化版本）
CREATE TABLE IF NOT EXISTS knowledge (
    id TEXT PRIMARY KEY,
    novel_id TEXT UNIQUE NOT NULL,
    version INTEGER DEFAULT 1,
    premise_lock TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (novel_id) REFERENCES novels(id) ON DELETE CASCADE
);

-- 章节摘要表（knowledge 中的 chapters）
CREATE TABLE IF NOT EXISTS chapter_summaries (
    id TEXT PRIMARY KEY,
    knowledge_id TEXT NOT NULL,
    chapter_number INTEGER NOT NULL,
    summary TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (knowledge_id) REFERENCES knowledge(id) ON DELETE CASCADE,
    UNIQUE(knowledge_id, chapter_number)
);

-- 索引
CREATE INDEX IF NOT EXISTS idx_chapters_novel_id ON chapters(novel_id);
CREATE INDEX IF NOT EXISTS idx_chapters_number ON chapters(novel_id, number);
CREATE INDEX IF NOT EXISTS idx_characters_novel_id ON characters(novel_id);
CREATE INDEX IF NOT EXISTS idx_characters_name ON characters(novel_id, name);
CREATE INDEX IF NOT EXISTS idx_triples_novel_id ON triples(novel_id);
CREATE INDEX IF NOT EXISTS idx_triples_subject ON triples(novel_id, subject);
CREATE INDEX IF NOT EXISTS idx_triples_predicate ON triples(predicate);
CREATE INDEX IF NOT EXISTS idx_triples_entity_type ON triples(novel_id, entity_type);
CREATE INDEX IF NOT EXISTS idx_triples_importance ON triples(importance);
CREATE INDEX IF NOT EXISTS idx_events_novel_id ON events(novel_id);
CREATE INDEX IF NOT EXISTS idx_events_chapter ON events(novel_id, chapter_number);
CREATE INDEX IF NOT EXISTS idx_locations_bible_id ON locations(bible_id);
CREATE INDEX IF NOT EXISTS idx_timeline_notes_bible_id ON timeline_notes(bible_id);
CREATE INDEX IF NOT EXISTS idx_style_notes_bible_id ON style_notes(bible_id);
CREATE INDEX IF NOT EXISTS idx_chapter_summaries_knowledge_id ON chapter_summaries(knowledge_id);
