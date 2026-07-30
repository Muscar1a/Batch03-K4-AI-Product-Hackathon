"""
LangGraph Workflow Builder
Biên dịch ChatbotState và các Node thành LangGraph Runnable StateGraph.
"""

from typing import Dict, Any
from .state import ChatbotState
from .nodes import (
    memory_extractor_and_router_node,
    kg_retriever_node,
    tool_execution_node,
    answer_synthesizer_node,
)

def route_intent(state: ChatbotState) -> str:
    """Điều hướng luồng dựa trên Intent."""
    intent = state.get("intent", "LOGISTICS")
    if intent == "EXECUTE_TOOL":
        return "tool_execution"
    return "kg_retriever"

def build_chatbot_graph():
    """
    Xây dựng luồng xử lý Agentic State Machine.
    Hỗ trợ cả fallback khi chưa cài langgraph hoặc biên dịch LangGraph StateGraph.
    """
    try:
        from langgraph.graph import StateGraph, END
        
        workflow = StateGraph(ChatbotState)
        
        workflow.add_node("router", memory_extractor_and_router_node)
        workflow.add_node("kg_retriever", kg_retriever_node)
        workflow.add_node("tool_execution", tool_execution_node)
        workflow.add_node("synthesizer", answer_synthesizer_node)
        
        workflow.set_entry_point("router")
        workflow.add_conditional_edges(
            "router",
            route_intent,
            {
                "kg_retriever": "kg_retriever",
                "tool_execution": "tool_execution"
            }
        )
        
        workflow.add_edge("kg_retriever", "synthesizer")
        workflow.add_edge("tool_execution", "synthesizer")
        workflow.add_edge("synthesizer", END)
        
        return workflow.compile()
    except ImportError:
        # Fallback nếu chưa cài gói langgraph
        return None
