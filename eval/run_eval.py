import json
import os
import sys

# Ensure root workspace is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from src.agent.graph import app
from src.agent.state import ChatbotState

def run_evaluation():
    golden_set_path = os.path.join(os.path.dirname(__file__), "golden_set.json")
    if not os.path.exists(golden_set_path):
        print(f"❌ Không tìm thấy file {golden_set_path}")
        return

    with open(golden_set_path, "r", encoding="utf-8") as f:
        cases = json.load(f)

    total_cases = len(cases)
    passed_cases = 0
    results = []

    print("==================================================================")
    print(f"🧪 CHẠY KIỂM THỬ TỰ ĐỘNG GOLDEN SET ({total_cases} CASES) — LANGGRAPH AGENT")
    print("==================================================================\n")

    for case in cases:
        cid = case["id"]
        query = case["query"]
        expected_intent = case["expected_intent"]
        expected_keywords = case["expected_keywords"]

        state: ChatbotState = {
            "messages": [{"role": "user", "content": query}],
            "user_id": f"eval_user_{cid}",
            "extracted_user_facts": [],
            "intent": "",
            "target_tool": None,
            "kg_triples": [],
            "retrieved_context": "",
            "final_response": "",
            "citations": []
        }

        output_state = app.invoke(state)
        actual_intent = output_state.get("intent", "")
        actual_response = output_state.get("final_response", "")

        # Check intent match & keyword match
        intent_pass = (actual_intent == expected_intent)
        keyword_pass = any(kw.lower() in actual_response.lower() for kw in expected_keywords)
        is_passed = intent_pass and keyword_pass

        if is_passed:
            passed_cases += 1
            status = "✅ PASS"
        else:
            status = "❌ FAIL"

        results.append({
            "id": cid,
            "query": query,
            "status": status,
            "intent_expected": expected_intent,
            "intent_actual": actual_intent,
            "response": actual_response[:100] + "..."
        })

        print(f"[{status}] Case #{cid:02d} ({case['category']}): '{query}'")
        if not is_passed:
            print(f"   -> Expected Intent: {expected_intent} | Got: {actual_intent}")
            print(f"   -> Expected Keywords: {expected_keywords}")
            print(f"   -> Response preview: {actual_response[:120]}...\n")

    accuracy = (passed_cases / total_cases) * 100
    print("\n==================================================================")
    print(f"📊 KẾT QUẢ ĐÁNH GIÁ (EVALUATION SUMMARY)")
    print(f"   - Tổng số kịch bản test: {total_cases}")
    print(f"   - Số case vượt qua (PASS): {passed_cases}/{total_cases}")
    print(f"   - Tỉ lệ chính xác (Accuracy): {accuracy:.1f}%")
    
    # Quality Bar Check (>= 90%)
    if accuracy >= 90.0:
        print("🎉 ĐẠT QUALITY BAR KHÓA HỌC (≥ 90%)!")
    else:
        print("⚠️ CHƯA ĐẠT QUALITY BAR KHÓA HỌC (Yêu cầu ≥ 90%). Cần tinh chỉnh thêm.")
    print("==================================================================")

if __name__ == "__main__":
    run_evaluation()
