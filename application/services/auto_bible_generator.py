"""自动 Bible 生成器 - 从小说标题生成完整的人物、地点、风格设定"""
import logging
import json
from typing import Dict, Any
from domain.ai.services.llm_service import LLMService, GenerationConfig
from domain.ai.value_objects.prompt import Prompt
from application.services.bible_service import BibleService

logger = logging.getLogger(__name__)


class AutoBibleGenerator:
    """自动 Bible 生成器

    根据小说标题，使用 LLM 生成：
    - 3-5 个主要人物（主角、配角、对手、导师等）
    - 2-3 个重要地点
    - 文风公约
    """

    def __init__(self, llm_service: LLMService, bible_service: BibleService):
        self.llm_service = llm_service
        self.bible_service = bible_service

    async def generate_and_save(
        self,
        novel_id: str,
        premise: str,
        target_chapters: int
    ) -> Dict[str, Any]:
        """生成并保存 Bible

        Args:
            novel_id: 小说 ID
            premise: 故事梗概/创意
            target_chapters: 目标章节数

        Returns:
            生成的 Bible 数据
        """
        logger.info(f"Generating Bible for novel: {premise[:50]}...")

        # 1. 创建空 Bible
        bible_id = f"{novel_id}-bible"
        self.bible_service.create_bible(bible_id, novel_id)

        # 2. 用 LLM 生成设定
        bible_data = await self._generate_bible_data(premise, target_chapters)

        # 3. 保存到 Bible
        await self._save_to_bible(novel_id, bible_data)

        logger.info(f"Bible generated successfully for {novel_id}")
        return bible_data

    async def _generate_bible_data(self, premise: str, target_chapters: int) -> Dict[str, Any]:
        """使用 LLM 生成 Bible 数据"""

        system_prompt = """你是资深网文策划编辑。根据用户提供的故事创意/梗概，生成完整的人物和世界设定。

**重要：只输出有效的 JSON，不要有任何其他文字。description 字段必须是单行文本，不能有换行符。**

要求：
1. 深入理解故事梗概，提取核心冲突、主题、世界观
2. 至少 3-5 个主要人物（主角、配角、对手、导师等），确保人物之间有冲突和互动
3. 每个人物：姓名、定位（主角/配角/对手/导师）、性格特点、目标动机
4. 至少 2-3 个重要地点，符合故事背景
5. 明确的文风公约（叙事视角、人称、基调、节奏）
6. 人物和地点要符合故事类型（现代都市/古代/玄幻/科幻等）
7. **所有 description 字段必须是单行文本，用逗号或分号分隔不同要点，不要使用换行符**

JSON 格式（不要有其他文字）：
{
  "characters": [
    {
      "name": "人物名",
      "role": "主角/配角/对手/导师",
      "description": "性格、背景、目标、特点，所有内容在一行内，用逗号分隔"
    }
  ],
  "locations": [
    {
      "name": "地点名",
      "type": "城市/建筑/区域",
      "description": "地点描述，单行文本"
    }
  ],
  "style": "第三人称有限视角，以XX视角为主。基调XX，节奏XX。避免XX。营造XX氛围。"
}"""

        user_prompt = f"""故事创意：{premise}

目标章节数：{target_chapters}章

请根据这个故事创意，生成完整的人物和世界设定。注意：
1. 从故事创意中提取关键信息（主角身份、核心能力、故事背景、主要冲突）
2. 人物要有层次，不能只有主角，要有配角、对手、导师等
3. 要有明确的冲突和对立面
4. 世界观要清晰，地点要符合故事类型
5. 文风公约要具体，明确叙事视角、基调、节奏
6. 适合网文读者，有代入感

只输出 JSON，不要有任何解释文字。"""

        prompt = Prompt(system=system_prompt, user=user_prompt)
        config = GenerationConfig(max_tokens=2048, temperature=0.7)

        result = await self.llm_service.generate(prompt, config)

        # 解析 JSON
        try:
            content = result.content.strip()

            # 移除可能的 markdown 代码块标记
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]

            content = content.strip()

            # 尝试找到第一个 { 和最后一个 }
            start = content.find('{')
            end = content.rfind('}')
            if start != -1 and end != -1:
                content = content[start:end+1]

            logger.info(f"Attempting to parse Bible JSON (length: {len(content)})")

            # 尝试直接解析
            try:
                bible_data = json.loads(content)
                logger.info(f"Successfully parsed Bible JSON")
                return bible_data
            except json.JSONDecodeError as e:
                # 如果失败，尝试修复常见问题
                logger.warning(f"First parse attempt failed: {e}, trying to repair JSON...")

                # 使用 json.loads 的 strict=False 模式
                import re
                # 移除字符串中的控制字符和多余的空白
                content = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', content)

                bible_data = json.loads(content, strict=False)
                logger.info(f"Successfully parsed Bible JSON after repair")
                return bible_data

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Bible JSON: {e}")
            logger.error(f"Raw content (first 1000 chars): {content[:1000]}")
            # 返回默认结构
            return {
                "characters": [
                    {
                        "name": "主角",
                        "role": "主角",
                        "description": "待补充"
                    }
                ],
                "locations": [
                    {
                        "name": "主要场景",
                        "type": "城市",
                        "description": "待补充"
                    }
                ],
                "style": "第三人称有限视角，轻松幽默"
            }

    async def _save_to_bible(self, novel_id: str, bible_data: Dict[str, Any]) -> None:
        """保存到 Bible"""

        # 添加人物
        for idx, char_data in enumerate(bible_data.get("characters", [])):
            character_id = f"{novel_id}-char-{idx+1}"
            self.bible_service.add_character(
                novel_id=novel_id,
                character_id=character_id,
                name=char_data["name"],
                description=f"{char_data['role']} - {char_data['description']}"
            )

        # 添加地点
        for idx, loc_data in enumerate(bible_data.get("locations", [])):
            location_id = f"{novel_id}-loc-{idx+1}"
            self.bible_service.add_location(
                novel_id=novel_id,
                location_id=location_id,
                name=loc_data["name"],
                description=loc_data["description"],
                location_type=loc_data.get("type", "场景")
            )

        # 添加风格笔记
        style = bible_data.get("style", "")
        if style:
            style_id = f"{novel_id}-style-1"
            self.bible_service.add_style_note(
                novel_id=novel_id,
                note_id=style_id,
                category="文风公约",
                content=style
            )
