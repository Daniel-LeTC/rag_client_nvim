import os
import sys
import warnings

from langchain_chroma import Chroma
from langchain_community.cross_encoders import HuggingFaceCrossEncoder
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_ollama import ChatOllama, OllamaEmbeddings

from config import COLLECTION_NAME, EMBEDDING_MODEL_NAME, MODEL_NAME, POLY_SYSTEM_PROMPT, VECTOR_DB_PATH

warnings.filterwarnings("ignore")


def format_docs(docs):
    return "\n\n".join(doc.page_content for doc in docs)


def main():
    # 1. Khởi tạo
    if not os.path.exists(VECTOR_DB_PATH):
        print(f"❌ Không tìm thấy Database tại {VECTOR_DB_PATH}!")
        return

    print(f"⚡ Đã tìm thấy DB tại {VECTOR_DB_PATH}. Load hàng nóng...")

    try:
        embedding_function = OllamaEmbeddings(model=EMBEDDING_MODEL_NAME)
        vectorstore = Chroma(
            persist_directory=VECTOR_DB_PATH, embedding_function=embedding_function, collection_name=COLLECTION_NAME
        )
    except Exception as e:
        print(f"💀 Lỗi load DB: {e}")
        return

    # 2. Setup Retriever & Reranker
    retriever = vectorstore.as_retriever(search_type="similarity", search_kwargs={"k": 20})

    print("🧠 Đang tải Reranker...")
    try:
        reranker = HuggingFaceCrossEncoder(model_name="BAAI/bge-reranker-base")
        print("✅ Reranker đã sẵn sàng.")
    except Exception as e:
        print(f"⚠️  Không load được Reranker: {e}. Dùng vector search thuần.")
        reranker = None

    # 3. Setup LLM
    print(f"🤖 Đang kích hoạt não bộ: {MODEL_NAME}...")
    llm = ChatOllama(model=MODEL_NAME, temperature=0, keep_alive="1h")
    prompt = ChatPromptTemplate.from_template(POLY_SYSTEM_PROMPT)

    print("\n" + "=" * 40)
    print("💬 POLYMATH BRO IS ONLINE (Gõ 'q' để té)")
    print("=" * 40)

    while True:
        try:
            query = input("\nMày: ").strip()
            if query.lower() in ["q", "quit", "exit"]:
                print("👋 Bye bro.")
                break
            if not query:
                continue

            print(f"\n🔍 Đang bới thùng rác tìm: '{query}'...")

            # --- RAG PIPELINE ---
            retrieved_docs = retriever.invoke(query)

            final_docs = retrieved_docs
            if reranker:
                try:
                    pairs = [[query, doc.page_content] for doc in retrieved_docs]
                    scores = reranker.score(pairs)
                    scored_docs = sorted(zip(retrieved_docs, scores), key=lambda x: x[1], reverse=True)
                    final_docs = [doc for doc, score in scored_docs[:5]]
                except Exception:
                    final_docs = retrieved_docs[:5]
            else:
                final_docs = retrieved_docs[:5]

            if not final_docs:
                print("\n🤖 Polymath Bot:")
                print("-" * 30)
                print("Tao lục tung thùng rác rồi mà không thấy thông tin gì liên quan. Mày đã note chưa?")
                print("-" * 30)
                continue

            context_text = format_docs(final_docs)
            chain = prompt | llm | StrOutputParser()

            print("\n🤖 Polymath Bot:")
            print("-" * 30)

            # Stream câu trả lời
            for chunk in chain.stream({"context": context_text, "question": query}):
                print(chunk, end="", flush=True)

            print("\n" + "-" * 30)

            # --- SHOW SOURCES (Minh bạch hóa thông tin) ---
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
            print(f"\n❌ Lỗi: {e}")


if __name__ == "__main__":
    main()
