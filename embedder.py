# embedder.py
import os
import numpy as np
from typing import List
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings

class Embedder:
  """ 텍스트 분할 및 OpenAI 임베딩 생성을 담당 """
  def __init__(self):
    if not os.getenv("OPENAI_API_KEY"): raise ValueError(".env 파일에 OPENAI_API_KEY가 설정되지 않았습니다.")
    self.text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
    self.embedding_model = OpenAIEmbeddings(model="text-embedding-3-small")
    print("✅ OpenAI 임베딩 모델 'text-embedding-3-small' 로드 완료.")

  def split_text(self, text: str) -> List[str]:
    return self.text_splitter.split_text(text)
    # return [text]

  def embed_texts(self, texts: List[str]) -> List[np.ndarray]:
    # embed_documents는 List[List[float]]를 반환하므로, 각 요소를 np.ndarray로 변환
    return [np.array(emb) for emb in self.embedding_model.embed_documents(texts)]
 
  def embed_query(self, text: str) -> np.ndarray:
    # 'list' object has no attribute 'read' 오류를 해결하기 위해 text를 명시적으로 문자열로 변환
    return np.array(self.embedding_model.embed_query(str(text)))
