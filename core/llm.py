"""LLM 服务 - 管理大语言模型调用"""

from typing import List, Dict, Any, Optional, AsyncGenerator
import os
from dotenv import load_dotenv

load_dotenv()


class LLMService:
    """大语言模型服务"""
    
    def __init__(
        self,
        provider: str = "openai",
        model: str = None,
        temperature: float = 0.3,
        max_tokens: int = 1500
    ):
        """
        初始化 LLM 服务
        
        Args:
            provider: 提供商 (openai)
            model: 模型名称
            temperature: 创造性程度 (0-1)
            max_tokens: 最大输出长度
        """
        self.provider = provider
        self.model = model or "gpt-4o-mini"  # 默认使用便宜且够用的模型
        self.temperature = temperature
        self.max_tokens = max_tokens
        self._client = None
        self._init_client()
    
    def _init_client(self):
        """初始化客户端"""
        if self.provider == "openai":
            try:
                from openai import OpenAI
                api_key = os.getenv("OPENAI_API_KEY")
                if not api_key:
                    raise ValueError("OPENAI_API_KEY not found")
                self._client = OpenAI(api_key=api_key)
            except ImportError:
                raise ImportError("Please install openai: pip install openai")
        else:
            raise ValueError(f"Unknown provider: {self.provider}")
    
    def complete(
        self,
        messages: List[Dict[str, str]],
        stream: bool = False
    ) -> str:
        """
        非流式完成
        
        Args:
            messages: 消息列表 [{"role": "user", "content": "..."}]
            stream: 是否流式输出
        
        Returns:
            生成的文本
        """
        if self.provider == "openai":
            return self._complete_openai(messages, stream)
        return ""
    
    def _complete_openai(self, messages: List[Dict[str, str]], stream: bool = False) -> str:
        """OpenAI 完成"""
        try:
            response = self._client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                stream=False
            )
            return response.choices[0].message.content or ""
        except Exception as e:
            print(f"LLM error: {e}")
            return f"[生成回答时出错: {str(e)}]"
    
    async def complete_stream(
        self,
        messages: List[Dict[str, str]]
    ) -> AsyncGenerator[str, None]:
        """
        流式完成
        
        Yields:
            生成的文本片段
        """
        if self.provider != "openai":
            yield "[流式输出仅支持 OpenAI]"
            return
        
        try:
            response = self._client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                stream=True
            )
            
            for chunk in response:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
        except Exception as e:
            yield f"[生成回答时出错: {str(e)}]"
    
    def answer_question(
        self,
        question: str,
        context: str,
        sources: List[Dict[str, Any]]
    ) -> str:
        """
        基于上下文回答问题
        
        Args:
            question: 用户问题
            context: 检索到的相关内容
            sources: 来源信息列表
        
        Returns:
            生成的回答
        """
        # 构造来源引用信息
        sources_info = "\n".join([
            f"[{i+1}] {s.get('title', 'Untitled')} (相关度: {s.get('similarity', 0):.1%})"
            for i, s in enumerate(sources)
        ])
        
        system_prompt = """你是一个基于知识库的AI助手。你的回答必须严格基于用户提供的参考资料。

核心原则：
1. 只使用提供的参考资料回答问题
2. 如果资料不足以回答问题，明确说明"根据现有资料无法完整回答此问题"
3. 不要编造信息，不要添加参考资料中没有的内容
4. 在回答末尾列出使用的来源编号
5. 使用中文回答"""

        user_prompt = f"""参考资料：
{context}

用户问题：{question}

请基于以上资料回答问题。回答要求：
1. 直接回答问题，不要绕弯子
2. 必要时引用来源 [1], [2] 等
3. 如果资料不充分，明确说明"根据现有资料无法完整回答此问题，请自行搜集更多资料。"

来源列表：
{sources_info}"""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        return self.complete(messages)


# 全局 LLM 服务实例
_llm_service: Optional[LLMService] = None


def get_llm_service() -> LLMService:
    """获取全局 LLM 服务实例"""
    global _llm_service
    if _llm_service is None:
        _llm_service = LLMService()
    return _llm_service
