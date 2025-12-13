import argparse
import hashlib
import os
import re
import sys
import textwrap

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_ollama import ChatOllama

# --- CẤU HÌNH ---
DEFAULT_NOTE_PATH = "/home/daniel/Projects/mind_dump/"
LLM_MODEL = "llama3.2:3b"

# --- REGEX PHÂN LOẠI FILE ---
# Tên file kiểu 8 chữ số, ví dụ: 20251213.md (dành cho Daily Dump/Chaos)
DAILY_DUMP_PATTERN = re.compile(r"^\d{8}\.md$", re.IGNORECASE)

# --- A. PROMPT CHO FILE DÀI (CHUYÊN GIA / DEEP RESEARCH) ---
DETAIL_TEMPLATE = """
Bạn là Trợ lý Phân tích Kiến thức. Tài liệu này là kiến thức CẤU TRÚC.
YÊU CẦU:
1. Tạo một bản **TÓM TẮT CHI TIẾT** (từ 2-3 câu) các ý chính, thuật toán, hoặc công thức quan trọng.
2. Tạo **MỘT DANH SÁCH DUY NHẤT** gồm 10-15 từ khóa bao quát **phạm vi (DOMAIN)** của tài liệu. Các từ khóa phải thuộc cấp độ lĩnh vực (ví dụ: 'Transformer', 'Attention Mechanism').

FORMAT OUTPUT:
Summary: [Tóm tắt chi tiết]
Keywords: [Keyword list]

Nội dung:
{text}
"""

# --- B. PROMPT CHO FILE NGẮN (CHAOS / DAILY DUMP) ---
SIMPLE_TEMPLATE = """
Bạn là Trợ lý RAG cho ghi chú cá nhân. Tài liệu này là ghi chú HỖN LOẠN, dùng để ghi nhớ nhanh.
YÊU CẦU:
1. Tóm tắt nội dung chính trong **ĐÚNG 1 CÂU TIẾNG VIỆT** (cực kỳ ngắn gọn).
2. Tạo **MỘT DANH SÁCH DUY NHẤT** gồm 10-15 từ khóa, tập trung vào **các thực thể (ENTITY)** được nhắc đến (ví dụ: tên người, sản phẩm, hành động, cảm xúc). Không cần từ khóa Domain nếu không rõ ràng.

FORMAT OUTPUT:
Summary: [Tóm tắt 1 câu]
Keywords: [Keyword list]

Nội dung:
{text}
"""


def calculate_md5(text):
    """Tính mã băm MD5 của văn bản để kiểm tra thay đổi"""
    return hashlib.md5(text.strip().encode("utf-8")).hexdigest()


def enrich_notes(note_path):
    """
    Đi tuần tra các file .md, phân loại theo tên file (YYYYMMDD.md vs Tên_Khác.md).
    """

    if not os.path.exists(note_path):
        return 0

    print(f"🔌 Đang kết nối với não bộ Ollama ({LLM_MODEL})...")
    try:
        llm = ChatOllama(model=LLM_MODEL, temperature=0)
    except Exception as e:
        print(f"❌ Không kết nối được Ollama: {e}")
        return 0

    metadata_pattern = re.compile(r"\n+\s*<!-- AI_METADATA\n(.*?)\n\s*-->", re.DOTALL)

    print(f"🕵️  Đang rà soát thay đổi tại: {note_path}")
    processed_count = 0
    skipped_count = 0

    for root, dirs, files in os.walk(note_path):
        for file in files:
            if file.endswith(".md"):
                file_path = os.path.join(root, file)
                filename = os.path.basename(file_path)  # Lấy tên file để kiểm tra

                try:
                    with open(file_path, encoding="utf-8") as f:
                        full_content = f.read()

                    # 1. Tách nội dung gốc
                    match = metadata_pattern.search(full_content)
                    user_content = full_content[: match.start()].strip() if match else full_content.strip()

                    if len(user_content) < 10:
                        continue

                    current_hash = calculate_md5(user_content)

                    # 2. KIỂM TRA HASH CŨ (Logic Versioning)
                    if match:
                        old_metadata_block = match.group(1)
                        hash_match = re.search(r"Content-Hash: ([a-f0-9]+)", old_metadata_block)
                        old_hash = hash_match.group(1) if hash_match else "old"

                        if current_hash == old_hash:
                            skipped_count += 1
                            continue
                        else:
                            print(f"📝 Phát hiện thay đổi trong: {file}. Re-indexing...")
                    else:
                        print(f"🔨 File mới: {file}. Đang xử lý...")

                    # 3. CHỌN PROMPT DỰA TRÊN TÊN FILE (LOGIC MỚI CỦA MÀY)
                    if DAILY_DUMP_PATTERN.match(filename):
                        template = SIMPLE_TEMPLATE
                        print(f"  [MODE: CHAOS] (Daily Dump: {filename})")
                    else:
                        template = DETAIL_TEMPLATE
                        print(f"  [MODE: EXPERT] (Structured: {filename})")

                    prompt = ChatPromptTemplate.from_template(template)
                    chain = prompt | llm | StrOutputParser()

                    # 4. Gọi AI xử lý
                    ai_response = chain.invoke({"text": user_content})

                    # 5. Ghi đè lại file
                    new_metadata = textwrap.dedent(f"""
                        <!-- AI_METADATA
                        Content-Hash: {current_hash}
                        {ai_response.strip()}
                        -->""")

                    with open(file_path, "w", encoding="utf-8") as f:
                        f.write(user_content + "\n\n" + new_metadata.strip())

                    print(f"✅ Đã cập nhật Metadata cho {file}")
                    processed_count += 1

                except Exception as e:
                    print(f"⚠️ Lỗi file {file}: {e}")

    print("-" * 30)
    print(f"🎉 Hoàn tất! Update: {processed_count} | Skip: {skipped_count}")
    return processed_count


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--path", type=str, default=DEFAULT_NOTE_PATH)
    args = parser.parse_args()
    enrich_notes(args.path)
