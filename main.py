import os
import sys
import warnings

from langchain_chroma import Chroma
from langchain_community.cross_encoders import HuggingFaceCrossEncoder
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough

# Import cả 2 thư viện
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_ollama import ChatOllama, OllamaEmbeddings

# Config an toàn
from config import (
    CLOUD_MODEL_NAME,
    COLLECTION_NAME,
    EMBEDDING_MODEL_NAME,
    GOOGLE_API_KEY,
    LOCAL_MODEL_NAME,
    POLY_SYSTEM_PROMPT,
    VECTOR_DB_PATH,
)

warnings.filterwarnings("ignore")


def format_docs(docs):
    return "\n\n".join(doc.page_content for doc in docs)


# --- HÀM KHỞI TẠO NÃO BỘ (HYBRID) ---
def get_llm(force_local=False):
    """
    Ưu tiên dùng Cloud (Gemini). Nếu force_local=True hoặc thiếu Key thì dùng Local (Qwen).
    """
    if not force_local and GOOGLE_API_KEY:
        try:
            print(f"☁️  Đang kết nối vệ tinh Google ({CLOUD_MODEL_NAME})...")
            llm = ChatGoogleGenerativeAI(
                model=CLOUD_MODEL_NAME,
                google_api_key=GOOGLE_API_KEY,
                temperature=0,
                convert_system_message_to_human=True,
            )
            return llm, "CLOUD"
        except Exception as e:
            print(f"⚠️  Lỗi kết nối Cloud: {e}. Chuyển sang Local.")

    print(f"🏠 Đang khởi động máy phát điện Local ({LOCAL_MODEL_NAME})...")
    llm = ChatOllama(model=LOCAL_MODEL_NAME, temperature=0, keep_alive="1h")
    return llm, "LOCAL"


def main():
    if not os.path.exists(VECTOR_DB_PATH):
        print(f"❌ Không tìm thấy Database tại {VECTOR_DB_PATH}!")
        return

    print(f"⚡ Đã tìm thấy DB tại {VECTOR_DB_PATH}. Load hàng nóng...")

    try:
        # Vẫn dùng Local Embedding cho nhanh & rẻ
        embedding_function = OllamaEmbeddings(model=EMBEDDING_MODEL_NAME)
        vectorstore = Chroma(
            persist_directory=VECTOR_DB_PATH, embedding_function=embedding_function, collection_name=COLLECTION_NAME
        )
    except Exception as e:
        print(f"💀 Lỗi load DB: {e}")
        return

    retriever = vectorstore.as_retriever(search_type="similarity", search_kwargs={"k": 30})

    print("🧠 Đang tải Reranker (CPU Mode)...")
    try:
        model_kwargs = {"device": "cpu"}
        reranker = HuggingFaceCrossEncoder(model_name="BAAI/bge-reranker-base", model_kwargs=model_kwargs)
        print("✅ Reranker đã sẵn sàng.")
    except Exception:
        reranker = None

    # Khởi tạo não bộ lần đầu
    llm, mode = get_llm()
    prompt = ChatPromptTemplate.from_template(POLY_SYSTEM_PROMPT)

    print("\n" + "=" * 40)
    print(f"💬 POLYMATH BRO IS ONLINE [{mode} MODE]")
    print("Gõ 'q' để té. Gõ 'swap' để đổi chế độ Cloud/Local.")
    print("=" * 40)

    while True:
        try:
            query = input("\nMày: ").strip()
            if query.lower() in ["q", "quit", "exit"]:
                print("👋 Bye bro.")
                break

            # Tính năng ẩn: Cho phép mày tự đổi mode
            if query.lower() == "swap":
                new_mode = not (mode == "CLOUD")  # Toggle
                llm, mode = get_llm(force_local=new_mode)
                print(f"🔄 Đã chuyển sang chế độ: {mode}")
                continue

            if not query:
                continue

            print(f"\n🔍 Đang bới thùng rác tìm: '{query}'...")

            # --- RAG RETRIEVAL ---
            retrieved_docs = retriever.invoke(query)
            final_docs = []

            # Rerank Logic
            if reranker:
                try:
                    pairs = [[query, doc.page_content] for doc in retrieved_docs]
                    scores = reranker.score(pairs)
                    scored_docs = sorted(zip(retrieved_docs, scores), key=lambda x: x[1], reverse=True)

                    # Threshold lọc nhẹ (-10.0 là lấy gần hết để AI tự lọc)
                    for doc, score in scored_docs[:7]:
                        if score > -10.0:
                            final_docs.append(doc)

                    if not final_docs and scored_docs:
                        final_docs = [scored_docs[0][0]]
                except:
                    final_docs = retrieved_docs[:5]
            else:
                final_docs = retrieved_docs[:5]

            if not final_docs:
                print("\n🤖 Polymath Bot:")
                print("-" * 30)
                print("Tao chịu. Không tìm thấy thông tin nào khớp cả.")
                continue

            context_text = format_docs(final_docs)
            chain = prompt | llm | StrOutputParser()

            print(f"\n🤖 Polymath Bot ({mode}):")
            print("-" * 30)

            # --- TRY/EXCEPT CHO LLM CALL (FALLBACK LOGIC) ---
            try:
                for chunk in chain.stream({"context": context_text, "question": query}):
                    print(chunk, end="", flush=True)
            except Exception as e:
                print(f"\n\n⚠️  Lỗi khi gọi {mode}: {e}")
                if mode == "CLOUD":
                    print("🔄 Đang chuyển sang LOCAL (Qwen) để cứu vãn tình thế...")
                    llm, mode = get_llm(force_local=True)  # Switch to Local
                    # Retry ngay lập tức với Local LLM
                    chain = prompt | llm | StrOutputParser()
                    for chunk in chain.stream({"context": context_text, "question": query}):
                        print(chunk, end="", flush=True)
                else:
                    print("💀 Local cũng chết. Mày check lại Ollama đi.")

            print("\n" + "-" * 30)

            # Evidence
            print("📚 Nguồn dữ liệu (Evidence):")
            seen_sources = set()
            for i, doc in enumerate(final_docs):
                source = os.path.basename(doc.metadata.get("source", "Unknown"))
                if source not in seen_sources:
                    print(f"   [{i + 1}] {source}")
                    seen_sources.add(source)
            print("-" * 30)

        except KeyboardInterrupt:
            print("\n👋 Bye!")
            break
        except Exception as e:
            print(f"\n❌ Lỗi hệ thống: {e}")


if __name__ == "__main__":
    main()
