"""
ETL Runner CLI Script
Chạy toàn bộ Pipeline ETL: Làm sạch dữ liệu Discord thô -> Deep Mining Triples -> Xuất data/extracted_triples.json
"""

import sys
import json
from pathlib import Path

# Thêm codebase vào sys.path để hỗ trợ import module
BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from codebase.src.etl.discord_cleaner import load_and_clean_json_file
from codebase.src.etl.kg_triples_extractor import extract_triples_from_corpus, ExtractionResult


def run_etl():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    data_dir = BASE_DIR / "data"
    crawl_dir = data_dir / "discord-crawl"
    
    print("=" * 60)
    print("🚀 ĐANG KHỞI CHẠY PIPELINE ETL (DATA ENGINE & TRIPLES MINING)")
    print("=" * 60)
    
    json_files = []
    
    # 1. Tìm các file JSON ở root data/ (ví dụ: 💬-chung.json)
    if data_dir.exists():
        for f in data_dir.glob("*.json"):
            json_files.append(f)
            
    # 2. Tìm tất cả các file JSON trong data/discord-crawl/
    if crawl_dir.exists():
        for f in crawl_dir.glob("*.json"):
            json_files.append(f)
            
    print(f"📁 Phát hiện tổng cộng: {len(json_files)} file JSON export từ Discord.")
    
    all_cleaned_messages = []
    raw_files_data = []
    total_raw_messages = 0
    total_kept_messages = 0
    total_filtered_bot = 0
    total_filtered_noise = 0
    
    for fpath in json_files:
        try:
            with open(fpath, "r", encoding="utf-8") as rf:
                fdata = json.load(rf)
                raw_files_data.append((fdata, fpath.name))
                
            msgs, meta = load_and_clean_json_file(fpath)
            stats = meta["stats"]
            
            total_raw_messages += stats["total"]
            total_kept_messages += stats["kept"]
            total_filtered_bot += stats["filtered_bot"]
            total_filtered_noise += stats["filtered_noise"] + stats["filtered_empty"]
            
            all_cleaned_messages.extend(msgs)
        except Exception as e:
            print(f"⚠️ Lỗi xử lý file {fpath.name}: {e}")

    filter_rate = ((total_raw_messages - total_kept_messages) / total_raw_messages * 100) if total_raw_messages > 0 else 0

    print("\n📊 BÁO CÁO THỐNG KÊ LÀM SẠCH DỮ LIỆU (DISCORD CLEANER):")
    print(f"   • Tổng số tin nhắn thô quét được: {total_raw_messages:,} tin nhắn")
    print(f"   • Số tin nhắn sạch giữ lại:        {total_kept_messages:,} tin nhắn")
    print(f"   • Số tin nhắn bot bị lọc:          {total_filtered_bot:,} tin nhắn")
    print(f"   • Số tin nhắn rác/nhiễu bị lọc:    {total_filtered_noise:,} tin nhắn")
    print(f"   🎯 TỶ LỆ LỌC RÁC & NHIỄU:           {filter_rate:.2f}%")
    
    print("\n🔍 ĐANG TRÍCH XUẤT KNOWLEDGE TRIPLES VÀ THỜI GIAN/CHỦ ĐỀ THREADS...")
    extraction_result: ExtractionResult = extract_triples_from_corpus(
        all_cleaned_messages,
        raw_files_data=raw_files_data,
        include_ground_truth=True
    )
    
    output_file = data_dir / "extracted_triples.json"
    output_data = {
        "metadata": {
            "total_raw_messages": total_raw_messages,
            "total_cleaned_messages": total_kept_messages,
            "noise_filter_rate_pct": round(filter_rate, 2),
            "extracted_triples_count": len(extraction_result.triples),
            "extracted_entities_count": len(extraction_result.entities)
        },
        "triples": [t.model_dump() for t in extraction_result.triples],
        "entities": [e.model_dump() for e in extraction_result.entities]
    }
    
    with open(output_file, "w", encoding="utf-8") as out_f:
        json.dump(output_data, out_f, ensure_ascii=False, indent=2)
        
    print(f"\n✅ ĐÃ XUẤT KẾT QUẢ THÀNH CÔNG:")
    print(f"   • Thư mục đầu ra: {output_file}")
    print(f"   • Tổng số Triples trích xuất:  {len(extraction_result.triples):,} triples")
    print(f"   • Tổng số Entities ghi nhận: {len(extraction_result.entities):,} entities")
    print("=" * 60)


if __name__ == "__main__":
    run_etl()
