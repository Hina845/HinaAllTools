import os, sys
import json
import numpy as np

import google.generativeai as genai
from qdrant_client import QdrantClient
from qdrant_client.http import models
from qdrant_client.http.models import Distance, VectorParams, PointStruct

API_KEY = "AIzaSyAbktggYoEBqg2UKyGBDfz61bqvoixWyqw"

genai.configure(api_key=API_KEY)

gemini_model = genai.GenerativeModel('gemini-2.0-flash')

class VectorStore:
    def __init__(self, collection_name: str = "documents", persist_directory: str = "./qdrant_db"):
        self.collection_name = collection_name
        self.persist_directory = persist_directory
        
        # Khởi tạo Qdrant client với file storage
        self.client = QdrantClient(path=persist_directory)
        
        # Tạo collection nếu chưa tồn tại
        try:
            self.client.get_collection(collection_name)
            print(f"Collection '{collection_name}' đã tồn tại")
        except:
            self.client.create_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(size=768, distance=Distance.COSINE)  # text-embedding-004 có 768 dimensions
            )
            print(f"Đã tạo collection '{collection_name}'")
        
        # Đếm số document hiện có
        collection_info = self.client.get_collection(collection_name)
        self.next_id = collection_info.points_count

    async def add(self, text: str):
        # Tạo embedding
        response = genai.embed_content(
            model="models/text-embedding-004",
            content=text
        )
        embedding = response['embedding']
        
        # Thêm vào collection
        point = PointStruct(
            id=self.next_id,
            vector=embedding,
            payload={"text": text}
        )
        
        self.client.upsert(
            collection_name=self.collection_name,
            points=[point]
        )
        self.next_id += 1

    def search(self, query_text: str, k: int = 3):
        query_response = genai.embed_content(
            model="models/text-embedding-004",
            content=query_text
        )
        query_embedding = query_response['embedding']
        
        search_result = self.client.query_points(
            collection_name=self.collection_name,
            query=query_embedding,
            limit=k
        )
        
        # Trả về nội dung gốc của các chunk được tìm thấy
        return [hit.payload["text"] for hit in search_result.points]

    def save(self, file_path: str = None):
        print(f"Dữ liệu đã được lưu tự động trong {self.persist_directory}")

    def load(self, file_path: str = None):
        try:
            # Kiểm tra xem collection có dữ liệu không
            collection_info = self.client.get_collection(self.collection_name)
            if collection_info.points_count > 0:
                print(f"Đã tải {collection_info.points_count} documents từ Qdrant")
                return True
            else:
                print("Qdrant collection trống. Bắt đầu tạo mới.")
                return False
        except Exception as e:
            print(f"Lỗi khi tải từ Qdrant: {e}")
            return False

# --- 3. Bộ xử lý dữ liệu (Data Processor) ---
class DataProcessor:
    def __init__(self, vector_store: VectorStore):
        self.vector_store = vector_store

    def chunk_text(self, text: str, chunk_size: int = 500):
        words = text.split() # Chia theo khoảng trắng
        chunks = []
        for i in range(0, len(words), chunk_size):
            chunks.append(' '.join(words[i:i + chunk_size]))
        return chunks

    async def process_and_embed(self, long_text: str):
        print("Đang chia nhỏ và nhúng nội dung...")
        chunks = self.chunk_text(long_text)
        for chunk in chunks:
            await self.vector_store.add(chunk)
        print(f"Đã xử lý và nhúng {len(chunks)} đoạn.")

# --- 4. Hệ thống RAG (Retrieval-Augmented Generation System) ---
class RAGSystem:
    def __init__(self, vector_store: VectorStore, gemini_model):
        self.vector_store = vector_store
        self.gemini_model = gemini_model

    async def ask_question(self, question: str):
        print(f"\nĐang tìm kiếm thông tin liên quan cho câu hỏi: \"{question}\"")
        # 1. Truy xuất các chunk liên quan
        related_chunks = self.vector_store.search(question, k=3) # Lấy 3 chunk liên quan nhất

        if not related_chunks:
            return "Xin lỗi, tôi không tìm thấy thông tin liên quan trong tài liệu đã cho."

        context = "\n\n---\n\n".join(related_chunks)

        prompt = (
            f"Dựa vào thông tin sau đây, hãy trả lời câu hỏi. "
            f"Nếu thông tin không đủ để trả lời, hãy thử tìm kiếm thông tin trên internet.\n\n"
            f"Thông tin:\n{context}\n\n"
            f"Câu hỏi: {question}\n\n"
            f"Trả lời:"
        )

        try:
            response = self.gemini_model.generate_content(
                contents=[{"parts": [{"text": prompt}]}],
                safety_settings={
                    "HARM_CATEGORY_HARASSMENT": "BLOCK_NONE",
                    "HARM_CATEGORY_HATE_SPEECH": "BLOCK_NONE",
                    "HARM_CATEGORY_SEXUALLY_EXPLICIT": "BLOCK_NONE",
                    "HARM_CATEGORY_DANGEROUS_CONTENT": "BLOCK_NONE",
                },
            )
            return response.text
        except Exception as e:
            print(f"Lỗi khi gọi Gemini API: {e}")
            return "Đã xảy ra lỗi khi cố gắng trả lời câu hỏi của bạn."

async def main():
    long_document = ""

    def get_config_path(filename):
        if getattr(sys, 'frozen', False):
            base_path = os.path.dirname(sys.executable)
        else:
            base_path = os.path.dirname(__file__)
        return os.path.join(base_path, filename)
        
    path = get_config_path('gttthcm.txt')
    with open(path, 'r', encoding='utf-8') as file:
        long_document = file.read()

    vector_store = VectorStore(collection_name="tthcm_docs", persist_directory="./tthcm_qdrant_db")
    data_processor = DataProcessor(vector_store)

    loaded = vector_store.load()

    if not loaded:
        if not long_document:
            print("Không có nội dung để xử lý. Vui lòng cung cấp nội dung.")
            return
        await data_processor.process_and_embed(long_document)
        vector_store.save()

    rag_system = RAGSystem(vector_store, gemini_model)


    while True:
        question = input("\nNhập câu hỏi của bạn (hoặc 'exit' để thoát): ")
        if question.lower() == 'exit':
            print("Thoát chương trình.")
            break
        answer = await rag_system.ask_question(question)
        print(f"\nCâu hỏi: {question}")
        print(f"Trả lời: {answer}")

import asyncio
if __name__ == "__main__":
    asyncio.run(main())