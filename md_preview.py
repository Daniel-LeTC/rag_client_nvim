import os
import subprocess
import sys
import tempfile

import markdown  # Khai báo nhưng không dùng, chỉ dùng MathJax CDN

# Lệnh này dùng để mở trình duyệt mặc định trên Linux (Fedora)
OPEN_CMD = "xdg-open"

# Template HTML cơ bản, chèn MathJax và nội dung Markdown
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Math Preview</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    
    <!-- Tailwind CSS cho giao diện đẹp và đọc dễ hơn -->
    <script src="https://cdn.tailwindcss.com"></script>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600&display=swap" rel="stylesheet">
    
    <!-- Script MathJax để render LaTeX Math -->
    <script>
      MathJax = {{
        tex: {{
          inlineMath: [['$', '$'], ['\\(', '\\)']],
          displayMath: [['$$', '$$'], ['\\[', '\\]']],
          packages: ['base', 'ams']
        }}
      }};
    </script>
    <script id="MathJax-script" async src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js"></script>

    <style>
        body {{ font-family: 'Inter', sans-serif; }}
        /* Tùy chỉnh màu sắc Markdown cho chế độ đọc ban đêm */
        pre {{ background-color: #2d3748; padding: 1rem; border-radius: 0.5rem; overflow-x: auto; }}
        img {{ max-width: 100%; height: auto; border-radius: 0.5rem; }}
        h1, h2, h3 {{ border-bottom: 1px solid #4a5568; padding-bottom: 0.3rem; margin-top: 2rem; }}
        table {{ width: 100%; border-collapse: collapse; margin: 1rem 0; }}
        th, td {{ border: 1px solid #4a5568; padding: 0.75rem; text-align: left; }}
    </style>
</head>
<body class="bg-gray-900 text-gray-200 min-h-screen p-8">
    <div class="max-w-4xl mx-auto p-6 bg-gray-800 rounded-xl shadow-2xl">
        <h1 class="text-3xl font-bold mb-4 text-indigo-400">📝 Live Markdown Preview</h1>
        <!-- Content placeholder -->
        <div id="content" class="prose max-w-none">
            {content_placeholder}
        </div>
    </div>
</body>
</html>
"""


def generate_html_content(md_content):
    """
    Chuyển Markdown sang HTML và thay thế nội dung trong template.
    Vì không dùng thư viện Markdown parser, ta chỉ cần wrap nội dung và MathJax sẽ lo phần công thức.
    """
    # Thay thế các ký tự đặc biệt để HTML không bị lỗi
    html_content = md_content.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")

    # Simple formatting: chuyển đổi tiêu đề và đoạn văn bản thô sơ
    html_content = html_content.replace("\n# ", "<h1>").replace("\n## ", "<h2>").replace("\n### ", "<h3>")
    html_content = html_content.replace("\n", "<p>")

    # Bảo toàn code blocks, nếu có
    # (Việc render Markdown phức tạp hơn cần thư viện, nhưng MathJax vẫn hoạt động tốt trên nền thô)

    return HTML_TEMPLATE.replace("{content_placeholder}", html_content)


def main():
    if len(sys.argv) < 2:
        print("Usage: md_preview.py <path/to/markdown/file>")
        sys.exit(1)

    md_file_path = sys.argv[1]

    if not os.path.exists(md_file_path):
        print(f"❌ File không tồn tại: {md_file_path}")
        sys.exit(1)

    # 1. Đọc nội dung Markdown
    with open(md_file_path, encoding="utf-8") as f:
        md_content = f.read()

    # 2. Tạo nội dung HTML
    html_output = generate_html_content(md_content)

    # 3. Ghi vào file tạm thời
    temp_dir = tempfile.gettempdir()
    temp_html_path = os.path.join(temp_dir, "nvim_math_preview.html")

    with open(temp_html_path, "w", encoding="utf-8") as f:
        f.write(html_output)

    # 4. Mở trình duyệt
    try:
        subprocess.run([OPEN_CMD, temp_html_path])
        print(f"✅ Đã mở preview trong trình duyệt. File tạm: {temp_html_path}")
    except FileNotFoundError:
        print(f"❌ Lệnh '{OPEN_CMD}' không được tìm thấy. Đảm bảo bạn đang dùng Linux và có xdg-open.")


if __name__ == "__main__":
    main()
