"""大模型服务模块"""

from langchain_openai import ChatOpenAI
from ..config import get_settings

# 全局大模型实例
_llm_instance = None


def get_llm() -> ChatOpenAI:
    """获取大模型实例（单例模式）"""
    global _llm_instance

    if _llm_instance is None:
        settings = get_settings()

        # 通过 LangChain 的 ChatOpenAI 连接任意 OpenAI 兼容端点
        _llm_instance = ChatOpenAI(
            model=settings.llm_model_id,
            api_key=settings.llm_api_key,
            base_url=settings.llm_base_url,
            temperature=0.2,
            timeout=settings.llm_timeout,
            streaming=True,
        )

        print("大模型服务初始化成功")
        print(f"   模型: {settings.llm_model_id}")
        print(f"   服务地址: {settings.llm_base_url}")

    return _llm_instance


def reset_llm():
    """重置大模型实例（用于测试或重新配置）"""
    global _llm_instance
    _llm_instance = None
