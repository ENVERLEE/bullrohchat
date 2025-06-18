import os
import oracledb
from database import OracleManager
import numpy as np
from dotenv import load_dotenv

def test_oracle_vector_db_integration():
    load_dotenv()
    print("--- Oracle Vector DB 통합 테스트 시작 ---")
    
    db = None
    try:
        db = OracleManager()
        
        print("\n1. 데이터베이스 초기화...")
        db.reset_database()
        print("   데이터베이스 초기화 완료.")

        # 더미 데이터 준비
        post_url = "http://example.com/test-post"
        title = "Test Post for Vector DB"
        content_hash = "test_hash_123"
        
        # 임베딩 차원과 일치하는 더미 벡터 생성
        embedding_dim = db.embedding_dim
        dummy_embedding_1 = np.random.rand(embedding_dim).tolist()
        dummy_embedding_2 = np.random.rand(embedding_dim).tolist()
        dummy_embedding_3 = np.random.rand(embedding_dim).tolist()

        chunks_data = [
            {"chunk_text": "This is the first test chunk about AI.", "embedding": dummy_embedding_1},
            {"chunk_text": "The second chunk discusses machine learning.", "embedding": dummy_embedding_2},
            {"chunk_text": "A third chunk talks about deep learning models.", "embedding": dummy_embedding_3},
        ]

        print("\n2. 더미 게시글 및 청크(벡터 포함) 삽입...")
        db.upsert_post_with_chunks(post_url, title, content_hash, chunks_data)
        print("   더미 데이터 삽입 완료.")

        print("\n3. 벡터 유사도 검색 테스트...")
        # 첫 번째 더미 임베딩과 유사한 쿼리 벡터 생성
        query_vector = [x + 0.01 for x in dummy_embedding_1] # 약간의 노이즈 추가
        
        similar_chunks = db.find_similar_chunks(query_vector, k=2)
        
        print("\n   검색 결과:")
        if similar_chunks:
            for text, distance in similar_chunks:
                print(f"     - 텍스트: '{text[:50]}...'")
                print(f"       거리: {distance}")
        else:
            print("     검색된 유사 청크가 없습니다.")

        # 예상 결과 확인 (간단한 검증)
        if similar_chunks and len(similar_chunks) > 0:
            # 가장 유사한 청크가 첫 번째 더미 청크와 관련이 있는지 확인
            if "first test chunk" in similar_chunks[0][0]:
                print("\n✅ 테스트 성공: Oracle Vector DB 통합이 정상적으로 작동합니다.")
            else:
                print("\n❌ 테스트 실패: 예상과 다른 검색 결과가 반환되었습니다.")
        else:
            print("\n❌ 테스트 실패: 검색 결과가 비어 있습니다.")

    except oracledb.Error as e:
        print(f"\n❌ Oracle DB 오류 발생: {e}")
        print("   .env 파일의 Oracle Cloud ATP 설정 및 DB 권한을 확인해주세요.")
    except Exception as e:
        print(f"\n❌ 예기치 않은 오류 발생: {e}")
    finally:
        if db:
            db.close()
            print("\n--- Oracle Vector DB 통합 테스트 종료 ---")

if __name__ == "__main__":
    test_oracle_vector_db_integration()
