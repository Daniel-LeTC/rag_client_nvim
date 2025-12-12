import argparse
import hashlib
import os
import re
import sys

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate

# Import các thư viện cần thiết từ LangChain & Ollama
from langchain_ollama import ChatOllama

# --- CẤU HÌNH MẶC ĐỊNH ---
DEFAULT_NOTE_PATH = "/home/daniel/Projects/mind_dump/"
LLM_MODEL = "llama3.2:3b"


def calculate_md5(text):
    """Tính mã băm MD5 của văn bản để kiểm tra thay đổi"""
    return hashlib.md5(text.strip().encode("utf-8")).hexdigest()


def enrich_notes(note_path):
    """
    Đi tuần tra các file .md, kiểm tra xem nội dung có thay đổi không.
    Nếu có (hoặc chưa có metadata) -> Gọi AI xử lý lại.
    """

    if not os.path.exists(note_path):
        print(f"❌ Đường dẫn không tồn tại: {note_path}")
        return 0

    print(f"🔌 Đang kết nối với não bộ Ollama ({LLM_MODEL})...")
    try:
        llm = ChatOllama(model=LLM_MODEL, temperature=0)
    except Exception as e:
        print(f"❌ Không kết nối được Ollama: {e}")
        return 0

    # Prompt mới: Yêu cầu không được bịa Hash, Hash do Python tự tính
    template = """
    Bạn là một trợ lý AI quản lý kiến thức.
    Nhiệm vụ: Đọc ghi chú và tạo Metadata chuẩn SEO cho RAG.
    
    YÊU CẦU:
    1. Tóm tắt 1 câu tiếng Việt.
    2. Liệt kê 10-15 keywords (Anh/Việt/Synonyms).
    
    FORMAT OUTPUT (Bắt buộc):
    Summary: [Tóm tắt]
    Keywords: [Keyword list]
    
    Nội dung:
    {text}
    """

    prompt = ChatPromptTemplate.from_template(template)
    chain = prompt | llm | StrOutputParser()

    print(f"🕵️  Đang rà soát thay đổi tại: {note_path}")
    processed_count = 0
    skipped_count = 0

    # Regex để tìm block metadata cũ ở cuối file
    # Cấu trúc: <!-- AI_METADATA ... --> (có thể có dòng Hash)
    metadata_pattern = re.compile(r"\n+<!-- AI_METADATA\n(.*?)\n-->", re.DOTALL)

    for root, dirs, files in os.walk(note_path):
        for file in files:
            if file.endswith(".md"):
                file_path = os.path.join(root, file)

                try:
                    with open(file_path, encoding="utf-8") as f:
                        full_content = f.read()

                    # 1. Tách nội dung gốc và metadata cũ
                    match = metadata_pattern.search(full_content)

                    if match:
                        # Đã có metadata -> Tách ra
                        user_content = full_content[: match.start()].strip()
                        old_metadata_block = match.group(1)

                        # Tìm hash cũ trong block metadata
                        hash_match = re.search(r"Content-Hash: ([a-f0-9]+)", old_metadata_block)
                        old_hash = hash_match.group(1) if hash_match else "old"

                        # Tính hash hiện tại
                        current_hash = calculate_md5(user_content)

                        # SO SÁNH
                        if current_hash == old_hash:
                            # Nội dung chưa đổi -> Bỏ qua
                            skipped_count += 1
                            continue
                        else:
                            print(f"📝 Phát hiện thay đổi trong: {file}. Re-indexing...")
                    else:
                        # Chưa có metadata
                        user_content = full_content.strip()
                        current_hash = calculate_md5(user_content)
                        print(f"🔨 File mới: {file}. Đang xử lý...")

                    # Bỏ qua file quá ngắn
                    if len(user_content) < 10:
                        continue

                    # 2. Gọi AI xử lý (Dùng user_content sạch, không dính metadata cũ)
                    ai_response = chain.invoke({"text": user_content})

                    # 3. Tạo block Metadata mới (Kèm Hash)
                    new_metadata = f"""
<!-- AI_METADATA
Content-Hash: {current_hash}
{ai_response.strip()}
-->"""

                    # 4. Ghi đè lại file (Nội dung gốc + Metadata mới)
                    with open(file_path, "w", encoding="utf-8") as f:
                        f.write(user_content + "\n" + new_metadata)

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
