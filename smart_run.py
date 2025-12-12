import argparse
import subprocess
import sys

# Import hàm enrich từ file enrich.py (cùng thư mục)
# Lưu ý: Nếu báo lỗi import, đảm bảo đang đứng đúng thư mục project
try:
    from enrich import DEFAULT_NOTE_PATH, enrich_notes
except ImportError:
    print("❌ Lỗi: Không tìm thấy file 'enrich.py'. Đảm bảo mày đang ở đúng thư mục project!")
    sys.exit(1)


def main():
    print("🤖 SMART RUNNER: Polymath Second Brain")
    print("=" * 40)

    # BƯỚC 1: Chạy Enrich để kiểm tra và xử lý file mới
    print(">>> [1/2] Checking & Enriching Notes...")
    try:
        # Gọi hàm enrich_notes, nó sẽ tự in log ra màn hình
        new_files_count = enrich_notes(DEFAULT_NOTE_PATH)
    except Exception as e:
        print(f"⚠️  Lỗi khi chạy enrich: {e}")
        new_files_count = 0

    # BƯỚC 2: Quyết định chạy RAG thế nào
    print("\n>>> [2/2] Launching RAG Chatbot...")

    cmd = ["uv", "run", "main.py"]

    # Logic thông minh: Có mới nới cũ
    if new_files_count > 0:
        print(f"\n📢 Phát hiện {new_files_count} note mới vừa được AI xử lý.")
        user_choice = input("❓ Bạn có muốn REBUILD database để cập nhật ngay không? [Y/n]: ").strip().lower()

        # Mặc định là Yes nếu ấn Enter
        if user_choice in ["", "y", "yes"]:
            print("⚡ Ok, thêm cờ --rebuild...")
            cmd.append("--rebuild")
        else:
            print("zzz Dùng database cũ (có thể thiếu tin mới)...")
    else:
        print("✅ Không có file mới. Dùng database hiện tại cho nhanh.")

    # Chuyển tiếp các tham số từ dòng lệnh (ví dụ câu hỏi chat)
    # sys.argv[1:] chứa các tham số sau tên script
    if len(sys.argv) > 1:
        cmd.extend(sys.argv[1:])

    # BƯỚC 3: Thực thi main.py
    print(f"▶️  Command: {' '.join(cmd)}")
    print("-" * 40)

    try:
        # Dùng subprocess để gọi main.py như một process con
        subprocess.run(cmd, check=False)
    except KeyboardInterrupt:
        print("\n👋 Bye bro!")
    except Exception as e:
        print(f"❌ Lỗi khi gọi main.py: {e}")


if __name__ == "__main__":
    main()
