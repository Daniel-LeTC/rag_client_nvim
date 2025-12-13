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

    # Lấy nhiều hơn để rerank (k=30)
    retriever = vectorstore.as_retriever(search_type="similarity", search_kwargs={"k": 30})

    print("🧠 Đang tải Reranker...")
    try:
        model_kwargs = {"device": "cpu"}
        reranker = HuggingFaceCrossEncoder(model_name="BAAI/bge-reranker-base", model_kwargs=model_kwargs)
        print("✅ Reranker đã sẵn sàng (CPU Mode).")
    except Exception as e:
        print(f"⚠️  Không load được Reranker: {e}")
        reranker = None

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

            final_docs = []
            if reranker:
                try:
                    pairs = [[query, doc.page_content] for doc in retrieved_docs]
                    scores = reranker.score(pairs)

                    scored_docs = sorted(zip(retrieved_docs, scores), key=lambda x: x[1], reverse=True)

                    print("   📊 Reranker Debug (Top 5):")

                    # --- NỚI LỎNG NGƯỠNG LỌC ---
                    # Hạ xuống -10.0 để hầu như không lọc gì cả, trừ khi quá tệ
                    THRESHOLD = -10.0

                    for i, (doc, score) in enumerate(scored_docs[:7]):
                        src = os.path.basename(doc.metadata.get("source", "Unknown"))
                        print(f"      [{i + 1}] Score: {score:.4f} | Source: {src}")

                        if score > THRESHOLD:
                            final_docs.append(doc)
                        else:
                            print(f"      ❌ [Loại bỏ do thấp hơn {THRESHOLD}]")

                    if not final_docs and scored_docs:
                        print("      ⚠️ Lấy tạm thằng đầu tiên dù điểm thấp.")
                        final_docs = [scored_docs[0][0]]

                except Exception as e:
                    print(f"Lỗi Rerank: {e}")
                    final_docs = retrieved_docs[:5]
            else:
                final_docs = retrieved_docs[:5]

            if not final_docs:
                print("\n🤖 Polymath Bot:")
                print("-" * 30)
                print("Tao chịu. Không tìm thấy thông tin nào khớp cả.")
                print("-" * 30)
                continue

            context_text = format_docs(final_docs)
            chain = prompt | llm | StrOutputParser()

            print("\n🤖 Polymath Bot:")
            print("-" * 30)

            for chunk in chain.stream({"context": context_text, "question": query}):
                print(chunk, end="", flush=True)

            print("\n" + "-" * 30)

            # Show Sources
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
