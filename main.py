import argparse
import os
import sys

# Import LangChain & Chroma & Ollama
from langchain_chroma import Chroma
from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain_core.documents import Document
from langchain_core.output_parsers import JsonOutputParser, StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_ollama import ChatOllama, OllamaEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

# --- CONFIG ---
NOTE_PATH = "/home/daniel/Projects/mind_dump/"
DB_PATH = "./chroma_db"
LLM_MODEL = "llama3.2:3b"
EMBED_MODEL = "mxbai-embed-large"


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

    # Chunk size 500 là điểm ngọt
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=500, chunk_overlap=100, add_start_index=True, separators=["\n## ", "\n### ", "\n- ", "\n", " "]
    )
    splits = text_splitter.split_documents(docs)

    vectorstore = Chroma.from_documents(
        documents=splits, embedding=OllamaEmbeddings(model=EMBED_MODEL), persist_directory=DB_PATH
    )
    print(f"✅ Đã index xong {len(splits)} chunks vào Database!")
    return vectorstore


def generate_multi_queries(original_query, llm):
    """
    Biến câu hỏi ngáo ngơ của mày thành 4 câu hỏi sát thủ (Tiếng Anh + Việt + Keyword).
    """
    print(f"🧠 Đang brainstorm để hiểu ý mày: '{original_query}'...")

    template = """
    Bạn là một trợ lý AI giúp tìm kiếm thông tin trong ghi chú cá nhân (Second Brain).
    Ghi chú thường chứa các thuật ngữ tiếng Anh (Coding, Biohacks, Workflow) và tiếng Việt.
    
    Nhiệm vụ: Dựa trên câu hỏi gốc của người dùng, hãy tạo ra 4 phiên bản câu hỏi tìm kiếm khác nhau để đảm bảo tìm thấy thông tin.
    
    Yêu cầu:
    1. Phiên bản 1: Dịch sang tiếng Anh (nếu câu gốc là Việt) hoặc ngược lại.
    2. Phiên bản 2: Tập trung vào từ khóa chuyên ngành (Technical Keywords).
    3. Phiên bản 3: Tìm các từ đồng nghĩa hoặc liên quan (Ví dụ: "ngủ nông" -> "insomnia", "sleep quality", "NSDR").
    4. Phiên bản 4: Giữ nguyên câu gốc.
    
    Chỉ trả về danh sách các câu hỏi ngăn cách bởi dấu xuống dòng. Không giải thích gì thêm.
    
    Câu hỏi gốc: {question}
    """

    prompt = ChatPromptTemplate.from_template(template)
    chain = prompt | llm | StrOutputParser()

    response = chain.invoke({"question": original_query})
    queries = [q.strip() for q in response.split("\n") if q.strip()]

    # In ra để mày thấy nó khôn thế nào
    print(f"🔍 AI đã sinh ra các từ khóa tìm kiếm: {queries}")
    return queries


def chat(query, vectorstore):
    """Hỏi xoáy đáp xoay - Version: Multi-Query Semantic Search"""

    llm = ChatOllama(model=LLM_MODEL, temperature=0)  # Temp thấp để logic chặt chẽ

    # 1. GENERATE QUERIES: Đẻ ra nhiều câu hỏi
    generated_queries = generate_multi_queries(query, llm)

    # 2. RETRIEVE: Quét tất cả các câu hỏi
    # Dùng list comprehension để tìm kiếm cho từng query
    unique_docs = {}
    retriever = vectorstore.as_retriever(search_kwargs={"k": 3})  # Mỗi query lấy 3 kết quả

    for q in generated_queries:
        docs = retriever.invoke(q)
        for doc in docs:
            # Dùng nội dung làm key để lọc trùng lặp (Deduplication)
            if doc.page_content not in unique_docs:
                unique_docs[doc.page_content] = doc

    final_docs = list(unique_docs.values())

    if not final_docs:
        print("❌ Retriever báo: Mày hỏi khó quá, tao brainstorm nát óc vẫn không tìm thấy note nào khớp.")
        return

    # 3. ANSWER: Tổng hợp thông tin
    template = """
    Mày là Trợ lý Second Brain. Dựa vào Context (đã được lọc từ nhiều nguồn), hãy trả lời câu hỏi.

    LUẬT:
    1. Trả lời bằng tiếng Việt.
    2. Tổng hợp thông tin từ các đoạn Context bên dưới.
    3. Nếu Context không liên quan -> Nói "Trong note chưa ghi".
    4. Trả lời ngắn gọn, style Coder.

    Context:
    {context}
    
    Câu hỏi gốc: {question}
    
    Trả lời:
    """
    prompt = ChatPromptTemplate.from_template(template)

    def format_docs(docs):
        return "\n\n".join(doc.page_content for doc in docs)

    rag_chain = (
        {"context": lambda x: format_docs(final_docs), "question": RunnablePassthrough()}
        | prompt
        | llm
        | StrOutputParser()
    )

    print(f"\n🤖 Polymath Bot ({LLM_MODEL}):")
    print("-" * 30)
    for chunk in rag_chain.stream(query):
        print(chunk, end="", flush=True)
    print("\n" + "-" * 30)

    # --- IN NGUỒN (CITATIONS) ---
    print("\n📄 NGUỒN DỮ LIỆU GỐC (Tổng hợp từ Multi-Query):")
    for i, doc in enumerate(final_docs[:5]):  # Chỉ in 5 cái đầu
        source = os.path.basename(doc.metadata.get("source", "Unknown"))
        snippet = doc.page_content.replace("\n", " ")[:100]
        print(f"[{i + 1}] ({source}) ...{snippet}...")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Chat với đống rác của mày")
    parser.add_argument("query", type=str, nargs="?", help="Câu hỏi")
    parser.add_argument("--rebuild", action="store_true", help="Xóa DB cũ, index lại từ đầu")

    args = parser.parse_args()

    vectorstore = load_and_index(force_rebuild=args.rebuild)

    if args.query:
        chat(args.query, vectorstore)
    else:
        while True:
            try:
                user_input = input("\nMày (gõ 'q' để té): ")
                if user_input.lower() in ["q", "exit", "quit"]:
                    break
                chat(user_input, vectorstore)
            except KeyboardInterrupt:
                break
