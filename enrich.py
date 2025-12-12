import argparse
import os
import sys

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate

# Import các thư viện cần thiết từ LangChain & Ollama
from langchain_ollama import ChatOllama

# --- CẤU HÌNH MẶC ĐỊNH ---
DEFAULT_NOTE_PATH = "/home/daniel/Projects/mind_dump/"
LLM_MODEL = "llama3.2:3b"


def enrich_notes(note_path):
    """
    Hàm này đi tuần tra các file .md, nhờ AI đọc hiểu và tiêm Metadata (Keywords + Summary) vào cuối file.
    Trả về: Số lượng file mới được xử lý.
    """

    # 1. Kiểm tra đường dẫn note
    if not os.path.exists(note_path):
        print(f"❌ Đường dẫn không tồn tại: {note_path}")
        return 0

    # 2. Khởi tạo kết nối với Ollama
    print(f"🔌 Đang kết nối với não bộ Ollama ({LLM_MODEL})...")
    try:
        llm = ChatOllama(model=LLM_MODEL, temperature=0)
    except Exception as e:
        print(f"❌ Không kết nối được Ollama: {e}")
        print("💡 Gợi ý: Mày đã chạy 'ollama serve' hoặc 'systemctl start ollama' chưa?")
        return 0

    # 3. Tạo Prompt để ép AI sinh Metadata chuẩn format
    template = """
    Bạn là một trợ lý AI quản lý kiến thức (Second Brain Librarian).
    Nhiệm vụ: Đọc ghi chú thô sơ bên dưới và tạo Metadata để giúp công cụ tìm kiếm (RAG) hoạt động tốt hơn.
    
    YÊU CẦU BẮT BUỘC:
    1. Tóm tắt nội dung chính trong đúng 1 câu tiếng Việt ngắn gọn.
    2. Liệt kê 10-15 từ khóa (Keywords) liên quan. Bao gồm:
       - Từ đồng nghĩa (ví dụ: "chaos" -> "hỗn loạn", "messy").
       - Thuật ngữ chuyên ngành (nếu có, cả Anh lẫn Việt).
       - Các từ khóa mà người dùng có thể sẽ search để tìm lại note này.
    
    FORMAT OUTPUT (Trả về y hệt khung dưới, không thêm lời dẫn):
    <!-- AI_METADATA
    Summary: [Nội dung tóm tắt]
    Keywords: [Keyword1, Keyword2, Keyword3, ...]
    -->
    
    Nội dung ghi chú cần xử lý:
    {text}
    """

    prompt = ChatPromptTemplate.from_template(template)
    chain = prompt | llm | StrOutputParser()

    # 4. Quét thư mục và xử lý từng file
    print(f"🕵️  Đang đi tuần tra khu vực: {note_path}")
    processed_count = 0
    skipped_count = 0

    for root, dirs, files in os.walk(note_path):
        for file in files:
            if file.endswith(".md"):
                file_path = os.path.join(root, file)

                try:
                    with open(file_path, encoding="utf-8") as f:
                        content = f.read()

                    # Bỏ qua file quá ngắn hoặc file rỗng
                    if len(content.strip()) < 50:
                        continue

                    # Bỏ qua file đã được xử lý (đã có tag Metadata)
                    if "<!-- AI_METADATA" in content:
                        skipped_count += 1
                        continue

                    print(f"🔨 Đang bơm thuốc cho file: {file}...")

                    # Gọi AI xử lý
                    metadata = chain.invoke({"text": content})

                    # Ghi nối (Append) vào cuối file
                    with open(file_path, "a", encoding="utf-8") as f:
                        # Thêm 2 dòng trống cho thoáng
                        f.write("\n\n" + metadata.strip())

                    print(f"✅ Đã xong: {file}")
                    processed_count += 1

                except Exception as e:
                    print(f"⚠️ Lỗi khi xử lý file {file}: {e}")

    # 5. Báo cáo kết quả
    print("-" * 30)
    print("🎉 Hoàn tất nhiệm vụ!")
    print(f"📊 Đã xử lý mới: {processed_count} file")
    print(f"⏩ Đã bỏ qua (làm rồi): {skipped_count} file")

    return processed_count


if __name__ == "__main__":
    # Setup tham số dòng lệnh cho chuyên nghiệp
    parser = argparse.ArgumentParser(description="Tool bơm Metadata cho ghi chú bằng AI")
    parser.add_argument(
        "--path", type=str, default=DEFAULT_NOTE_PATH, help="Đường dẫn folder note (mặc định lấy trong code)"
    )

    args = parser.parse_args()

    enrich_notes(args.path)
