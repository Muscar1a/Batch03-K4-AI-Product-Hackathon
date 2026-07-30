from typing import TypedDict, List, Dict, Any, Optional

class UserFact(TypedDict):
    fact_type: str  # "OS", "GROUP", "STUCK_ISSUE", "PREFERENCE"
    value: str
    timestamp: str

class ChatbotState(TypedDict):
    # Core Chat History
    messages: List[Dict[str, str]]
    user_id: str
    
    # Extracted Conversation Memory
    extracted_user_facts: List[UserFact]
    
    # Intent & Routing
    intent: str  # "LOGISTICS", "TECH_BUG", "EXECUTE_TOOL", "AMBIGUOUS"
    target_tool: Optional[str]
    
    # Graph & Context Retrieval
    kg_triples: List[Dict[str, Any]]
    retrieved_context: str
    
    # Output Generation
    final_response: str
    citations: List[str]
