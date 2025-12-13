import os
import re

# CẤU HÌNH ĐƯỜNG DẪN FOLDER NOTE CỦA MÀY VÀO ĐÂY
NOTES_DIR = "/home/daniel/Projects/mind_dump/"  # Sửa lại cho đúng đường dẫn máy mày


def clean_metadata_from_files(directory):
    print(f"🧹 Đang quét dọn metadata cũ tại: {directory}")
    count = 0

    # Regex để tìm block AI_METADATA (bao gồm cả multiline)
    # Tìm từ <!-- AI_METADATA đến -->
    metadata_pattern = re.compile(r"<!--\s*AI_METADATA.*?-->", re.DOTALL)

    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith(".md"):
                file_path = os.path.join(root, file)

                try:
                    with open(file_path, encoding="utf-8") as f:
                        content = f.read()

                    # Kiểm tra xem có metadata không
                    if metadata_pattern.search(content):
                        # Xóa metadata
                        new_content = metadata_pattern.sub("", content).strip()

                        # Ghi lại file sạch
                        with open(file_path, "w", encoding="utf-8") as f:
                            f.write(new_content)
                            # Đảm bảo có dòng trống ở cuối file cho đẹp
                            f.write("\n")

                        print(f"✅ Đã tẩy não: {file}")
                        count += 1
                except Exception as e:
                    print(f"❌ Lỗi khi xử lý {file}: {e}")

    print("------------------------------------------------")
    print(f"🎉 Hoàn tất! Đã xóa metadata khỏi {count} file.")
    print("👉 Bước tiếp theo: Xóa folder 'chroma_db' và chạy lại 'smart_run.py'.")


if __name__ == "__main__":
    if os.path.exists(NOTES_DIR):
        confirm = input(f"⚠️  CẢNH BÁO: Hành động này sẽ xóa metadata cũ trong {NOTES_DIR}. Tiếp tục? (y/n): ")
        if confirm.lower() == "y":
            clean_metadata_from_files(NOTES_DIR)
        else:
            print("Đã hủy.")
    else:
        print("❌ Đường dẫn không tồn tại. Sửa lại biến NOTES_DIR trong code đi bro.")
