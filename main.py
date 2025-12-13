import argparse
import os
import sys

import torch
from langchain_chroma import Chroma
from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_ollama import ChatOllama, OllamaEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

# Import Reranker Libraries
from sentence_transformers import CrossEncoder

# --- CONFIG ---
NOTE_PATH = "/home/daniel/Projects/mind_dump/"
DB_PATH = "./chroma_db"
LLM_MODEL = "llama3:8b"
EMBED_MODEL = "mxbai-embed-large"
RERANKER_MODEL = "cross-encoder/ms-marco-TinyBERT-L-2"


def load_and_index(force_rebuild=False):
    """Đọc note, băm nhỏ và nhét vào Vector DB"""
    if os.path.exists(DB_PATH) and not force_rebuild:
        print(f"⚡ Đã tìm thấy DB tại {DB_PATH}. Load lên xài luôn...")
        return Chroma(persist_directory=DB_PATH, embedding_function=OllamaEmbeddings(model=EMBED_MODEL))

    print("♻️  Đang quét note và tạo index mới (chờ tí nha bro)...")

    if not os.path.exists(NOTE_PATH):
        print(f"❌ Đường dẫn {NOTE_PATH} không tồn tại!")
        sys.exit(1)

    loader = DirectoryLoader(NOTE_PATH, glob="**/*.md", loader_cls=TextLoader)
    docs = loader.load()

    if not docs:
        print("❌ Không tìm thấy file .md nào để học cả!")
        sys.exit(1)

    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,  # Kích thước mỗi miếng
        chunk_overlap=100,  # Gối đầu nhau để giữ ngữ cảnh
        add_start_index=True,
        separators=["\n## ", "\n### ", "\n- ", "\n", " "],
    )
    splits = text_splitter.split_documents(docs)

    vectorstore = Chroma.from_documents(
        documents=splits, embedding=OllamaEmbeddings(model=EMBED_MODEL), persist_directory=DB_PATH
    )
    print(f"✅ Đã index xong {len(splits)} chunks vào Database!")
    return vectorstore


def chat(query, vectorstore, reranker):  # <-- THÊM reranker vào tham số
    """Hỏi xoáy đáp xoay - Version: Sniper Elite"""

    # 1. Quét rộng (Retriever - Hút bụi)
    retriever = vectorstore.as_retriever(
        search_type="similarity",
        search_kwargs={"k": 15},  # Lấy 15 chunks để đảm bảo không bỏ sót cái nào
    )

    print(f"\n🔍 Đang bới thùng rác tìm: '{query}'...")

    try:
        raw_docs = retriever.invoke(query)
    except Exception:
        raw_docs = []

    if not raw_docs:
        print("❌ Retriever báo: Không tìm thấy bất kỳ đoạn nào khớp!")
        retrieved_docs = []
    else:
        # --- FIX 2: Lọc Metadata VÔ DỤNG ---
        filtered_docs = [
            doc
            for doc in raw_docs
            if "AI_METADATA" not in doc.page_content  # Lọc các đoạn chỉ chứa metadata vô dụng
        ]

        if not filtered_docs:
            print("❌ Lọc Metadata: Không còn nội dung hữu ích nào để rerank!")
            retrieved_docs = []
        else:
            # 2. Rerank (Lọc cát đãi vàng)

            # Tạo cặp [query, doc.page_content]
            sentence_pairs = [[query, doc.page_content] for doc in filtered_docs]

            # Chấm điểm
            scores = reranker.predict(sentence_pairs)

            # Ghép điểm vào doc và sắp xếp
            scored_docs = sorted(
                [(score, doc) for score, doc in zip(scores, filtered_docs)], key=lambda x: x[0], reverse=True
            )

            # 3. Lấy TOP 5 CHẤT LƯỢNG NHẤT (Output cho LLM)
            # Chỉ lấy 5 cái có điểm Reranker cao nhất
            retrieved_docs = [doc for score, doc in scored_docs[:5]]

    if not retrieved_docs:
        # Nếu đã qua Reranker mà vẫn không có gì, thì báo lỗi.
        print("❌ Reranker/Filter loại hết vì không có đoạn nào liên quan (hoặc điểm quá thấp)!")

    # 4. Setup LLM
    llm = ChatOllama(model=LLM_MODEL, temperature=0.1)

    # 5. PROMPT: Giữ nguyên prompt V3 đã sửa
    template = """
    Mày là Trợ lý Second Brain thông minh. Mày phải trả lời chính xác, mạch lạc.
    
    QUY TẮC BẤT KHẢ XÂM PHẠM:
    1. Bắt buộc dùng TIẾNG VIỆT để trả lời.
    2. CHỈ sử dụng các thông tin nằm trong phần "Context" bên dưới.
    3. Trả lời bằng cách TỔNG HỢP và DIỄN GIẢI lại nội dung.
    4. Trả lời dưới dạng GẠCH ĐẦU DÒNG.
    5. Nếu Context không có bất kỳ thông tin nào liên quan -> Trả lời ngắn gọn: "Thông tin này chưa được ghi lại trong các note của mày."

    Context:
    {context}
    
    Câu hỏi: {question}
    
    Trả lời:
    """
    prompt = ChatPromptTemplate.from_template(template)

    # 6. Chain
    def format_docs(docs):
        return "\n\n".join(doc.page_content for doc in docs)

    rag_chain = (
        {"context": lambda x: format_docs(retrieved_docs), "question": RunnablePassthrough()}
        | prompt
        | llm
        | StrOutputParser()
    )

    # 7. Run & Print Answer
    print(f"\n🤖 Polymath Bot ({LLM_MODEL}):")
    print("-" * 30)

    for chunk in rag_chain.stream(query):
        print(chunk, end="", flush=True)
    print("\n" + "-" * 30)

    # --- IN NGUỒN (CITATIONS) ---
    print("\n📄 NGUỒN DỮ LIỆU GỐC (Đã Rerank):")
    if retrieved_docs:
        for i, doc in enumerate(retrieved_docs):
            source = doc.metadata.get("source", "Unknown")
            snippet = doc.page_content.replace("\n", " ")[:100]
            filename = os.path.basename(source)
            print(f"[{i + 1}] ({filename}) ...{snippet}...")
    else:
        print("(Không tìm thấy nguồn nào khớp)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Chat với đống rác của mày")
    parser.add_argument("query", type=str, nargs="?", help="Câu hỏi")
    parser.add_argument("--rebuild", action="store_true", help="Xóa DB cũ, index lại từ đầu")

    args = parser.parse_args()

    # Load DB
    vectorstore = load_and_index(force_rebuild=args.rebuild)

    # --- FIX 1: Khởi tạo Reranker 1 LẦN duy nhất ---
    print("🧠 Đang tải Reranker (chỉ 1 lần)...")
    try:
        # Nếu model đã tải về, nó sẽ khởi tạo rất nhanh
        reranker = CrossEncoder(RERANKER_MODEL)
        print("✅ Reranker đã sẵn sàng.")
    except Exception as e:
        print(f"❌ Lỗi tải Reranker: {e}. Vui lòng kiểm tra uv add sentence-transformers torch.")
        sys.exit(1)

    # Chat logic
    if args.query:
        chat(args.query, vectorstore, reranker)  # <-- THÊM reranker vào lệnh gọi
    else:
        while True:
            try:
                user_input = input("\nMày (gõ 'q' để té): ")
                if user_input.lower() in ["q", "exit", "quit"]:
                    break
                chat(user_input, vectorstore, reranker)  # <-- THÊM reranker vào lệnh gọi
            except KeyboardInterrupt:
                break
