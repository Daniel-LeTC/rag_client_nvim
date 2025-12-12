import argparse
import os
import subprocess
import sys

# Import hàm enrich và đường dẫn note từ file enrich.py
try:
    from enrich import DEFAULT_NOTE_PATH, enrich_notes
except ImportError:
    print("❌ Lỗi: Không tìm thấy file 'enrich.py'. Đảm bảo mày đang ở đúng thư mục project!")
    sys.exit(1)


def sync_to_github(repo_path):
    """
    Hàm này đóng vai Shipper, đẩy hàng lên GitHub
    """
    print(f"\n🚀 Đang đồng bộ hóa kho {repo_path} lên GitHub...")

    # Kiểm tra xem có folder .git không
    if not os.path.exists(os.path.join(repo_path, ".git")):
        print("⚠️  Kho note chưa có Git (git init). Bỏ qua vụ push.")
        return

    try:
        # 1. Git Add (Gom hàng)
        subprocess.run(["git", "add", "."], cwd=repo_path, check=True)

        # 2. Git Commit (Đóng gói)
        # check=False vì nếu không có gì thay đổi git commit sẽ exit code 1 -> kệ nó
        commit_msg = "🤖 AI Auto-Enrich: Bơm metadata và cập nhật note"
        result = subprocess.run(["git", "commit", "-m", commit_msg], cwd=repo_path, capture_output=True)

        if result.returncode != 0:
            print("zzz Không có gì thay đổi để commit.")
            return

        # 3. Git Push (Gửi hàng)
        print("☁️  Đang đẩy lên mây (Pushing)...")
        subprocess.run(["git", "push"], cwd=repo_path, check=True)
        print("✅ Done! Dữ liệu đã an toàn trên GitHub.")

    except subprocess.CalledProcessError as e:
        print(f"❌ Lỗi Git: {e}")
    except Exception as e:
        print(f"❌ Lỗi lạ: {e}")


def main():
    print("🤖 SMART RUNNER: Polymath Second Brain")
    print("=" * 40)

    # BƯỚC 1: Chạy Enrich
    print(">>> [1/3] Checking & Enriching Notes...")
    try:
        new_files_count = enrich_notes(DEFAULT_NOTE_PATH)
    except Exception as e:
        print(f"⚠️  Lỗi khi chạy enrich: {e}")
        new_files_count = 0

    # BƯỚC 2: Auto Sync Git (Nếu có file mới hoặc file bị sửa đổi bởi AI)
    # Kể cả enrich trả về 0 file mới, có thể mày đã sửa tay nội dung note, nên cứ thử sync cho chắc
    print("\n>>> [2/3] Git Backup Protocol...")
    sync_to_github(DEFAULT_NOTE_PATH)

    # BƯỚC 3: Quyết định chạy RAG
    print("\n>>> [3/3] Launching RAG Chatbot...")

    cmd = ["uv", "run", "main.py"]

    # Logic thông minh: Có mới nới cũ
    if new_files_count > 0:
        print(f"\n📢 Phát hiện {new_files_count} note vừa được AI xử lý.")
        user_choice = input("❓ Bạn có muốn REBUILD database để cập nhật ngay không? [Y/n]: ").strip().lower()

        if user_choice in ["", "y", "yes"]:
            print("⚡ Ok, thêm cờ --rebuild...")
            cmd.append("--rebuild")

    # Chuyển tiếp tham số (câu hỏi)
    if len(sys.argv) > 1:
        cmd.extend(sys.argv[1:])

    print(f"▶️  Command: {' '.join(cmd)}")
    print("-" * 40)

    try:
        subprocess.run(cmd, check=False)
    except KeyboardInterrupt:
        print("\n👋 Bye bro!")


if __name__ == "__main__":
    main()
