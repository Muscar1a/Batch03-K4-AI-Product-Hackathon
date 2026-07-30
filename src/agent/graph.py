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
    clarification_node,
    guardrail_refusal_node,
)

def route_intent(state: ChatbotState) -> str:
    """Điều hướng luồng dựa trên Intent."""
    intent = state.get("intent", "LOGISTICS")
    if intent == "OUT_OF_SCOPE":
        return "guardrail_refusal"
    elif intent == "AMBIGUOUS":
        return "clarification"
    elif intent == "EXECUTE_TOOL":
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
        workflow.add_node("clarification", clarification_node)
        workflow.add_node("guardrail_refusal", guardrail_refusal_node)
        workflow.add_node("synthesizer", answer_synthesizer_node)
        
        workflow.set_entry_point("router")
        workflow.add_conditional_edges(
            "router",
            route_intent,
            {
                "kg_retriever": "kg_retriever",
                "tool_execution": "tool_execution",
                "clarification": "clarification",
                "guardrail_refusal": "guardrail_refusal"
            }
        )
        
        workflow.add_edge("kg_retriever", "synthesizer")
        workflow.add_edge("tool_execution", "synthesizer")
        workflow.add_edge("clarification", END)
        workflow.add_edge("guardrail_refusal", END)
        workflow.add_edge("synthesizer", END)
        
        return workflow.compile()
    except ImportError:
        return None

# Đăng ký instance app chính cho hệ thống
app = build_chatbot_graph()

if app is None:
    class DummyApp:
        def invoke(self, state: ChatbotState) -> ChatbotState:
            router_out = memory_extractor_and_router_node(state)
            state.update(router_out)
            
            intent = state.get("intent")
            if intent == "OUT_OF_SCOPE":
                refusal_out = guardrail_refusal_node(state)
                state.update(refusal_out)
                return state
            elif intent == "AMBIGUOUS":
                clarify_out = clarification_node(state)
                state.update(clarify_out)
                return state
            elif intent == "EXECUTE_TOOL":
                tool_out = tool_execution_node(state)
                state.update(tool_out)
            else:
                kg_out = kg_retriever_node(state)
                state.update(kg_out)
                
            synth_out = answer_synthesizer_node(state)
            state.update(synth_out)
            return state
            
    app = DummyApp()
