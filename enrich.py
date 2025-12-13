import hashlib
import json
import os
import re

from langchain_chroma import Chroma

# --- FIX IMPORT Ở ĐÂY ---
from langchain_core.documents import Document
from langchain_ollama import ChatOllama, OllamaEmbeddings
from langchain_text_splitters import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter

# Import Config
from config import COLLECTION_NAME, EMBEDDING_MODEL_NAME, MODEL_NAME, NOTES_DIRECTORY, VECTOR_DB_PATH

# Pattern nhận diện metadata cũ
METADATA_PATTERN = re.compile(r"<!--\s*AI_METADATA(.*?)-->", re.DOTALL)
# Pattern nhận diện file Daily Note (VD: 20251213.md)
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
    """
    Sinh Metadata thông minh.
    """
    llm = ChatOllama(model=MODEL_NAME, temperature=0.1)
    prompt = f"""
    You are a Personal Knowledge Assistant.
    Analyze this note ({file_name}) and provide:
    1. A Vietnamese Summary (2-3 sentences).
    2. Keywords (English/Vietnamese) for search optimization.

    Content snippet:
    {content[:3000]}
    
    Output strictly in this format:
    Summary: <text>
    Keywords: <k1, k2, k3>
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


# --- CHUNKING STRATEGY ---


def chunk_daily_note(content, source):
    """
    Chiến thuật cho Daily Dump (Systematic Chaos):
    Cắt theo Heading (##) để tách biệt các topic rời rạc trong ngày.
    """
    headers_to_split_on = [("#", "Header 1"), ("##", "Topic"), ("###", "Sub-topic")]

    markdown_splitter = MarkdownHeaderTextSplitter(headers_to_split_on=headers_to_split_on)
    base_metadata = {"source": source, "type": "daily_log"}

    docs = markdown_splitter.split_text(content)

    for doc in docs:
        doc.metadata.update(base_metadata)

    return docs


def chunk_topic_note(content, source):
    """
    Chiến thuật cho Deep Work Note.
    """
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000, chunk_overlap=200, separators=["\n## ", "\n### ", "\n", " "]
    )
    docs = text_splitter.create_documents([content], metadatas=[{"source": source, "type": "deep_work"}])
    return docs


def process_notes():
    print(f"🔌 Kết nối não bộ: {MODEL_NAME}")
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

                    # 1. Sinh Metadata & Update File Gốc
                    ai_meta = generate_ai_metadata(clean_content, file)
                    update_file_with_metadata(file_path, content, ai_meta, current_hash)

                    # 2. CHUNKING
                    chunks = []
                    if DAILY_NOTE_PATTERN.match(file):
                        print("   ↳ Daily Note Detected -> Header Splitting")
                        chunks = chunk_daily_note(clean_content, file_path)
                    else:
                        print("   ↳ Topic Note Detected -> Recursive Splitting")
                        chunks = chunk_topic_note(clean_content, file_path)

                    # 3. Inject AI Keywords
                    for chunk in chunks:
                        chunk.metadata["ai_summary"] = ai_meta

                    # 4. Đẩy vào Vector DB
                    if chunks:
                        vectorstore.add_documents(chunks)
                        updated += 1

                except Exception as e:
                    print(f"❌ Lỗi file {file}: {e}")

    print("-" * 30)
    print(f"🎉 Xong! Updated: {updated} | Skipped: {skipped}")


if __name__ == "__main__":
    process_notes()
