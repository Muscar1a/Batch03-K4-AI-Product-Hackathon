from typing import Dict, Any
from src.agent.state import ChatbotState
from src.agent.nodes import (
    memory_extractor_and_router_node,
    kg_retriever_node,
    tool_execution_node,
    ticket_confirmation_node,
    clarification_node,
    guardrail_refusal_node,
    answer_synthesizer_node
)

class LangGraphAgentApp:
    """
    State Machine Engine điều phối luồng hội thoại theo kiến trúc LangGraph.
    """
    def invoke(self, state: ChatbotState) -> ChatbotState:
        current_state = dict(state)
        
        # Node 1: Memory Extractor & Router
        router_update = memory_extractor_and_router_node(current_state)
        current_state.update(router_update)
        
        intent = current_state.get("intent", "LOGISTICS")
        
        # Routing Conditional Edges
        if intent == "OUT_OF_SCOPE":
            refusal_update = guardrail_refusal_node(current_state)
            current_state.update(refusal_update)
            return current_state
            
        elif intent == "AMBIGUOUS":
            clarify_update = clarification_node(current_state)
            current_state.update(clarify_update)
            return current_state

        elif intent == "ASK_TICKET_CONFIRMATION":
            ticket_prompt_update = ticket_confirmation_node(current_state)
            current_state.update(ticket_prompt_update)
            return current_state
            
        elif intent == "EXECUTE_TOOL":
            tool_update = tool_execution_node(current_state)
            current_state.update(tool_update)
            
            synth_update = answer_synthesizer_node(current_state)
            current_state.update(synth_update)
            return current_state
            
        else:  # LOGISTICS or TECH_BUG
            kg_update = kg_retriever_node(current_state)
            current_state.update(kg_update)
            
            synth_update = answer_synthesizer_node(current_state)
            current_state.update(synth_update)
            return current_state

# Instantiated runnable agent app
app = LangGraphAgentApp()
