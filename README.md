🧠 Polymath Second Brain - Local RAG Setup

Hệ thống Second Brain chạy local 100%, sử dụng Neovim để ghi chú và AI để tìm kiếm/tổng hợp thông tin.

🛠️ Yêu cầu hệ thống (Prerequisites)

OS: Linux (Fedora/Ubuntu/Arch...) hoặc WSL2.

GPU: NVIDIA RTX 3060 (6GB VRAM) trở lên là mượt.

Python: 3.10+ (Khuyên dùng uv để quản lý package).

🦙 1. Cài đặt Ollama (AI Engine)

Chạy lệnh sau để cài đặt (Script chính chủ của Ollama):

curl -fsSL [https://ollama.com/install.sh](https://ollama.com/install.sh) | sh


Quản lý Service (Systemd)

Sau khi cài xong, đảm bảo Ollama chạy ngầm cùng hệ thống:

# Khởi động service
sudo systemctl start ollama

# Bật tự động chạy khi mở máy
sudo systemctl enable ollama


Check trạng thái: systemctl status ollama

📥 2. Tải Models (The Brains)

Chúng ta cần 2 model: một cái để Nghĩ (LLM) và một cái để Nhìn (Embedding).

A. LLM Model: Llama 3.2 3B

Lý do: Nhỏ, nhẹ, nhanh, context window lớn (128k), chạy mượt trên Laptop GPU 6GB mà không làm nóng máy.

ollama pull llama3.2:3b


B. Embedding Model: mxbai-embed-large

Lý do: Tốt nhất trong tầm giá cho RAG. Hỗ trợ đa ngôn ngữ tốt hơn nomic, hiểu ngữ nghĩa sâu hơn. Dimension 1024.

ollama pull mxbai-embed-large


🚀 3. Cài đặt Python Dependencies

Dự án này dùng uv cho sạch sẽ và nhanh.

# 1. Cài uv (nếu chưa có)
curl -LsSf [https://astral.sh/uv/install.sh](https://astral.sh/uv/install.sh) | sh

# 2. Sync thư viện
uv sync


🎮 4. Sử dụng

Chạy thủ công (Terminal):

# Chat tự động (tự check file mới, tự bơm metadata, tự git push)
uv run smart_run.py

# Chat với câu hỏi cụ thể
uv run smart_run.py "ghi chú hỗn loạn là gì?"


Chạy trong Neovim:

:Ask <câu hỏi>: Mở cửa sổ chat Floating Window.

:Enrich: Chạy tool bơm Metadata thủ công.

Created by Polymath Bro Architecture.
