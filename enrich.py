import hashlib
import json
import os
import re

from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_ollama import ChatOllama, OllamaEmbeddings
from langchain_text_splitters import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter

# Import Config
from config import COLLECTION_NAME, EMBEDDING_MODEL_NAME, LOCAL_MODEL_NAME, NOTES_DIRECTORY, VECTOR_DB_PATH

METADATA_PATTERN = re.compile(r"<!--\s*AI_METADATA(.*?)-->", re.DOTALL)
DAILY_NOTE_PATTERN = re.compile(r"^\d{8}\.md$")


def calculate_file_hash(content):
    return hashlib.md5(content.encode("utf-8")).hexdigest()


def get_existing_metadata(content):
    match = METADATA_PATTERN.search(content)
    return match.group(1).strip() if match else None


def extract_hash_from_metadata(metadata_text):
    if not metadata_text:
        return None
    match = re.search(r"Content-Hash:\s*([a-f0-9]+)", metadata_text)
    return match.group(1) if match else None


def generate_ai_metadata(content, file_name):
    llm = ChatOllama(model=LOCAL_MODEL_NAME, temperature=0.1)
    prompt = f"""
    You are a Knowledge Librarian.
    Analyze this note ({file_name}) and extract:
    1. A short Summary (Vietnamese).
    2. Top 5 specific Keywords (English/Vietnamese).

    Content snippet:
    {content[:3000]}
    
    Output format:
    Summary: ...
    Keywords: ...
    """
    try:
        response = llm.invoke(prompt)
        return response.content
    except Exception as e:
        print(f"❌ AI Error on {file_name}: {e}")
        return "Summary: Error.\nKeywords: error"


def update_file_with_metadata(file_path, original_content, new_metadata_body, file_hash):
    metadata_block = f"""
<!-- AI_METADATA
Content-Hash: {file_hash}
{new_metadata_body}
-->
"""
    clean_content = METADATA_PATTERN.sub("", original_content).strip()
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(clean_content + "\n\n" + metadata_block)


# --- CHUNKING STRATEGY (NÂNG CẤP) ---


def chunk_daily_note(content, source):
    # B1: Cắt theo Heading trước (Lấy Context Topic)
    headers_to_split_on = [("#", "Header 1"), ("##", "Topic"), ("###", "Sub-topic")]
    markdown_splitter = MarkdownHeaderTextSplitter(headers_to_split_on=headers_to_split_on)

    # Cắt sơ bộ
    initial_docs = markdown_splitter.split_text(content)

    # Xử lý trường hợp file "trần chuồng" (Không có Header nào)
    if not initial_docs:
        initial_docs = [Document(page_content=content, metadata={})]

    final_docs = []

    # B2: Cắt mịn (Recursive) nếu chunk còn quá to
    recursive_splitter = RecursiveCharacterTextSplitter(
        chunk_size=800,  # Kích thước vừa phải để từ khóa cô đọng
        chunk_overlap=100,
        separators=["\n- ", "\n", " ", ""],  # Ưu tiên cắt ở gạch đầu dòng
    )

    base_metadata = {"source": source, "type": "daily_log"}

    for doc in initial_docs:
        # Lấy Topic từ Header (nếu có)
        topic = doc.metadata.get("Topic", "General Log")
        sub = doc.metadata.get("Sub-topic", "")
        file_name = os.path.basename(source)

        # Tạo Context String để Inject
        context_str = f"DAILY LOG: {file_name}\nTOPIC: {topic}"
        if sub:
            context_str += f" > {sub}"

        # Nếu chunk này dài quá 800 ký tự -> Cắt nhỏ tiếp
        if len(doc.page_content) > 1000:
            sub_chunks = recursive_splitter.create_documents([doc.page_content])
            for sub_chunk in sub_chunks:
                # Inject Context vào từng mảnh nhỏ
                sub_chunk.page_content = f"{context_str}\n---\n{sub_chunk.page_content}"
                sub_chunk.metadata.update(doc.metadata)  # Giữ lại metadata heading
                sub_chunk.metadata.update(base_metadata)
                final_docs.append(sub_chunk)
        else:
            # Nếu chunk nhỏ gọn rồi thì Inject luôn
            doc.page_content = f"{context_str}\n---\n{doc.page_content}"
            doc.metadata.update(base_metadata)
            final_docs.append(doc)

    return final_docs


def chunk_topic_note(content, source):
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000, chunk_overlap=200, separators=["\n## ", "\n### ", "\n", " "]
    )
    docs = text_splitter.create_documents([content], metadatas=[{"source": source, "type": "deep_work"}])
    return docs


def process_notes():
    print(f"🔌 Kết nối não bộ: {LOCAL_MODEL_NAME}")
    print(f"📂 Quét folder: {NOTES_DIRECTORY}")

    embedding_function = OllamaEmbeddings(model=EMBEDDING_MODEL_NAME)
    vectorstore = Chroma(
        persist_directory=VECTOR_DB_PATH, embedding_function=embedding_function, collection_name=COLLECTION_NAME
    )

    updated = 0
    skipped = 0

    for root, dirs, files in os.walk(NOTES_DIRECTORY):
        dirs[:] = [d for d in dirs if not d.startswith(".")]

        for file in files:
            if file.endswith(".md"):
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, encoding="utf-8") as f:
                        content = f.read()

                    clean_content = METADATA_PATTERN.sub("", content).strip()
                    current_hash = calculate_file_hash(clean_content)

                    existing_meta = get_existing_metadata(content)
                    old_hash = extract_hash_from_metadata(existing_meta)

                    if old_hash == current_hash:
                        print(f"⏩ Skip: {file}")
                        skipped += 1
                        continue

                    print(f"🔄 Processing: {file}...")

                    # 1. Sinh Metadata
                    ai_meta = generate_ai_metadata(clean_content, file)
                    update_file_with_metadata(file_path, content, ai_meta, current_hash)

                    # 2. CHUNKING (Gọi hàm đã update)
                    chunks = []
                    is_daily = False

                    if DAILY_NOTE_PATTERN.match(file):
                        chunks = chunk_daily_note(clean_content, file_path)
                        is_daily = True
                    else:
                        chunks = chunk_topic_note(clean_content, file_path)
                        is_daily = False

                    # 3. Context Injection (Cho luồng Topic)
                    # (Luồng Daily đã inject bên trong hàm chunk_daily_note rồi)
                    file_name_only = os.path.basename(file_path)
                    keywords = "General"
                    if "Keywords:" in ai_meta:
                        try:
                            keywords = ai_meta.split("Keywords:")[1].strip().split("\n")[0]
                        except:
                            pass

                    if not is_daily:
                        for chunk in chunks:
                            chunk.metadata["original_content"] = chunk.page_content
                            chunk.metadata["ai_summary"] = ai_meta
                            chunk.page_content = f"SOURCE DOCUMENT: {file_name_only}\nCONTEXT KEYWORDS: {keywords}\n---\n{chunk.page_content}"

                    # 4. Đẩy vào DB
                    if chunks:
                        vectorstore.add_documents(chunks)
                        updated += 1

                except Exception as e:
                    print(f"❌ Lỗi file {file}: {e}")

    print("-" * 30)
    print(f"🎉 Xong! Updated: {updated} | Skipped: {skipped}")


if __name__ == "__main__":
    process_notes()
