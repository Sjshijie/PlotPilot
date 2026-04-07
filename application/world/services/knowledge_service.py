"""Knowledge application service"""
import logging
from typing import Optional, List, Dict, Any
from domain.knowledge.story_knowledge import StoryKnowledge
from domain.knowledge.chapter_summary import ChapterSummary
from domain.knowledge.knowledge_triple import KnowledgeTriple
from domain.knowledge.repositories.knowledge_repository import KnowledgeRepository
from domain.shared.exceptions import EntityNotFoundError

logger = logging.getLogger(__name__)


class KnowledgeService:
    """知识服务

    处理知识图谱的业务逻辑
    """

    def __init__(self, knowledge_repository: KnowledgeRepository):
        """初始化服务

        Args:
            knowledge_repository: 知识仓储
        """
        self.knowledge_repository = knowledge_repository

    def get_knowledge(self, novel_id: str) -> StoryKnowledge:
        """获取知识图谱

        Args:
            novel_id: 小说ID

        Returns:
            故事知识

        Raises:
            EntityNotFoundError: 如果知识图谱不存在
        """
        knowledge = self.knowledge_repository.get_by_novel_id(novel_id)
        if knowledge is None:
            # 返回空的知识图谱而不是抛出异常，保持向后兼容
            logger.info(f"Knowledge not found for {novel_id}, returning empty knowledge")
            return StoryKnowledge(novel_id=novel_id)
        return knowledge

    def update_knowledge(self, novel_id: str, data: Dict[str, Any]) -> StoryKnowledge:
        """更新知识图谱

        Args:
            novel_id: 小说ID
            data: 知识数据

        Returns:
            更新后的故事知识
        """
        # 构建章节摘要列表
        chapters = [
            ChapterSummary(
                chapter_id=ch["chapter_id"],
                summary=ch.get("summary", ""),
                key_events=ch.get("key_events", ""),
                open_threads=ch.get("open_threads", ""),
                consistency_note=ch.get("consistency_note", ""),
                beat_sections=ch.get("beat_sections", []),
                sync_status=ch.get("sync_status", "draft")
            )
            for ch in data.get("chapters", [])
        ]

        # 构建知识三元组列表
        facts = [
            KnowledgeTriple(
                id=fact["id"],
                subject=fact.get("subject", ""),
                predicate=fact.get("predicate", ""),
                object=fact.get("object", ""),
                chapter_id=fact.get("chapter_id"),
                note=fact.get("note", ""),
                entity_type=fact.get("entity_type"),
                importance=fact.get("importance"),
                location_type=fact.get("location_type"),
                description=fact.get("description"),
                first_appearance=fact.get("first_appearance"),
                related_chapters=fact.get("related_chapters", []),
                tags=fact.get("tags", []),
                attributes=fact.get("attributes", {}),
                confidence=fact.get("confidence"),
                source_type=fact.get("source_type"),
                subject_entity_id=fact.get("subject_entity_id"),
                object_entity_id=fact.get("object_entity_id"),
            )
            for fact in data.get("facts", [])
        ]

        # 创建或更新知识图谱
        knowledge = StoryKnowledge(
            novel_id=novel_id,
            version=data.get("version", 1),
            premise_lock=data.get("premise_lock", ""),
            chapters=chapters,
            facts=facts
        )

        # 使用 save_all 方法保存
        logger.info(f"KnowledgeService: Calling save_all for {novel_id}, facts: {len(facts)}")
        self.knowledge_repository.save_all(novel_id, data)
        logger.info(f"Updated knowledge for {novel_id}: {len(chapters)} chapters, {len(facts)} facts")
        return knowledge

    def search_knowledge(self, novel_id: str, query: str, k: int = 6) -> Dict[str, Any]:
        """搜索知识图谱

        Args:
            novel_id: 小说ID
            query: 搜索查询
            k: 返回结果数量

        Returns:
            搜索结果
        """
        # TODO: 实现向量搜索功能
        # 当前返回空结果，保持API兼容性
        logger.warning(f"Knowledge search not implemented yet for {novel_id}, query: {query}")
        return {"hits": []}

    def upsert_chapter_summary(
        self,
        novel_id: str,
        chapter_id: int,
        summary: str = "",
        key_events: str = "",
        open_threads: str = "",
        consistency_note: str = "",
        beat_sections: List[str] = None,
        micro_beats: List[Dict[str, Any]] = None,
        sync_status: str = "draft"
    ) -> StoryKnowledge:
        """添加或更新章节摘要

        Args:
            novel_id: 小说ID
            chapter_id: 章节号
            summary: 章末总结
            key_events: 关键事件
            open_threads: 未解问题
            consistency_note: 一致性说明
            beat_sections: 节拍列表
            micro_beats: 微观节拍列表
            sync_status: 同步状态

        Returns:
            更新后的故事知识
        """
        knowledge = self.get_knowledge(novel_id)

        chapter = ChapterSummary(
            chapter_id=chapter_id,
            summary=summary,
            key_events=key_events,
            open_threads=open_threads,
            consistency_note=consistency_note,
            beat_sections=beat_sections or [],
            micro_beats=micro_beats or [],
            sync_status=sync_status
        )

        knowledge.add_or_update_chapter(chapter)
        self.knowledge_repository.save(knowledge)
        logger.info(f"Upserted chapter summary for {novel_id}, chapter {chapter_id}")
        return knowledge

    def upsert_fact(
        self,
        novel_id: str,
        fact_id: str,
        subject: str,
        predicate: str,
        object: str,
        chapter_id: Optional[int] = None,
        note: str = ""
    ) -> StoryKnowledge:
        """添加或更新知识三元组

        Args:
            novel_id: 小说ID
            fact_id: 三元组ID
            subject: 主语
            predicate: 谓词
            object: 宾语
            chapter_id: 章节号
            note: 备注

        Returns:
            更新后的故事知识
        """
        knowledge = self.get_knowledge(novel_id)

        fact = KnowledgeTriple(
            id=fact_id,
            subject=subject,
            predicate=predicate,
            object=object,
            chapter_id=chapter_id,
            note=note
        )

        knowledge.add_or_update_fact(fact)
        self.knowledge_repository.save(knowledge)
        logger.info(f"Upserted fact for {novel_id}: {fact_id}")
        return knowledge
