import os
import subprocess
import sys
import time
from pathlib import Path

# --- CẤU HÌNH ĐƯỜNG DẪN TUYỆT ĐỐI ---
# Lấy thư mục chứa file smart_run.py này làm gốc
BASE_DIR = Path(__file__).parent.resolve()

# Đường dẫn tới các script con (nằm cùng thư mục)
ENRICH_SCRIPT = BASE_DIR / "enrich.py"
MAIN_SCRIPT = BASE_DIR / "main.py"

# Lấy đường dẫn notes từ biến môi trường (nếu có), không thì dùng config mặc định
# Lưu ý: Script này chạy độc lập, nhưng ta có thể import config nếu thích.
# Ở đây ta hardcode nhẹ để check folder notes cho Git
NOTES_DIR = os.getenv("NOTES_DIR", "/home/daniel/Projects/mind_dump/")


def print_step(step, msg):
    print(f"\n{'=' * 50}")
    print(f"🚀 [BƯỚC {step}] {msg}")
    print(f"{'=' * 50}")


def run_command(command, description):
    """Chạy lệnh shell và in màu mè"""
    print(f"▶️  Thực thi: {description}...")
    try:
        # Sử dụng sys.executable để đảm bảo dùng đúng python của venv hiện tại
        if command[0] == "python":
            command[0] = sys.executable

        result = subprocess.run(command, cwd=BASE_DIR)

        if result.returncode != 0:
            print(f"❌ Lỗi khi chạy {description}. Mã lỗi: {result.returncode}")
            return False
        return True
    except FileNotFoundError:
        print(f"❌ Không tìm thấy file hoặc lệnh. Kiểm tra lại đường dẫn: {command}")
        return False
    except KeyboardInterrupt:
        print("\n🛑 Đã dừng thủ công.")
        return False


def git_backup():
    """Tự động commit và push notes lên Git"""
    if not os.path.exists(NOTES_DIR):
        print(f"⚠️  Folder {NOTES_DIR} không tồn tại. Bỏ qua backup Git.")
        return

    print_step("2/3", "Backup não bộ lên Cloud (Git)...")

    # Check xem có thay đổi gì không
    status = subprocess.run(["git", "status", "--porcelain"], cwd=NOTES_DIR, capture_output=True, text=True)

    if not status.stdout.strip():
        print("zzz Không có gì thay đổi để commit. Ngủ tiếp.")
        return

    print("🔥 Phát hiện thay đổi note. Đang backup...")
    try:
        subprocess.run(["git", "add", "."], cwd=NOTES_DIR, check=True)
        subprocess.run(
            ["git", "commit", "-m", f"Brain Dump: {time.strftime('%Y-%m-%d %H:%M')}"], cwd=NOTES_DIR, check=True
        )
        # Push (Uncomment dòng dưới nếu mày đã setup remote)
        # subprocess.run(["git", "push"], cwd=NOTES_DIR, check=True)
        print("✅ Backup hoàn tất!")
    except subprocess.CalledProcessError as e:
        print(f"⚠️  Lỗi Git: {e}")


def main():
    print("🤖 SMART RUNNER: Polymath Second Brain")
    print(f"📂 Working Dir: {BASE_DIR}")

    # 1. Kiểm tra file tồn tại
    if not ENRICH_SCRIPT.exists():
        print(f"❌ CHẾT TOANG: Không tìm thấy '{ENRICH_SCRIPT.name}'")
        print("👉 Mày chưa copy file enrich.py vào thư mục này hả?")
        return
    if not MAIN_SCRIPT.exists():
        print(f"❌ CHẾT TOANG: Không tìm thấy '{MAIN_SCRIPT.name}'")
        return

    # 2. Chạy Enrich (Build Data)
    print_step("1/3", "Nạp dữ liệu (Enriching)...")
    if not run_command(["python", str(ENRICH_SCRIPT)], "Enrich Data"):
        print("⚠️  Enrich gặp lỗi. Có muốn chạy tiếp RAG không? (y/n)")
        if input("> ").lower() != "y":
            return

    # 3. Chạy Git Backup (Optional)
    git_backup()

    # 4. Chạy Main RAG (Chat)
    print_step("3/3", "Khởi động Polymath Chatbot...")
    run_command(["python", str(MAIN_SCRIPT)], "RAG Chatbot")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n👋 Bye bro.")
