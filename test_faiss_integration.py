import os
import json
import numpy as np
from database import OracleManager
import oracledb # oracledb 모듈 임포트

# .env 파일 로드 (실제 환경에서는 dotenv 등을 사용)
# 테스트를 위해 필요한 환경 변수를 설정해야 합니다.
# 예: os.environ['ORACLE_USER'] = 'your_user'
# os.environ['ORACLE_PASSWORD'] = 'your_password'
# os.environ['ORACLE_ATP_DSN'] = 'your_dsn'
# os.environ['ORACLE_WALLET_PATH'] = 'your_wallet_path'
# os.environ['ORACLE_WALLET_PASSWORD'] = 'your_wallet_password'

def run_faiss_integration_test():
    db_manager = None
    try:
        print("--- FAISS 통합 테스트 시작 ---")
        db_manager = OracleManager()
        print("데이터베이스 매니저 초기화 성공.")

        # 1. 데이터베이스 초기화 (테이블 및 FAISS 파일 정리)
        print("\n1. 데이터베이스 초기화 중...")
        db_manager.reset_database()
        print("데이터베이스 초기화 완료.")

        # 2. 샘플 데이터 삽입 테스트
        print("\n2. 샘플 게시물 및 청크 데이터 삽입 중...")
        sample_post_url = "http://example.com/test-post-1"
        sample_title = "테스트 게시물 1"
        sample_content_hash = "hash123"
        
        # 임베딩 차원 1536에 맞는 더미 임베딩 생성
        chunks_data = [
            {"chunk_text": "첫 번째 청크 내용입니다.", "embedding": np.random.rand(1536).tolist()},
            {"chunk_text": "두 번째 청크 내용입니다.", "embedding": np.random.rand(1536).tolist()},
            {"chunk_text": "세 번째 청크 내용입니다.", "embedding": np.random.rand(1536).tolist()},
        ]
        
        db_manager.upsert_post_with_chunks(sample_post_url, sample_title, sample_content_hash, chunks_data)
        print("샘플 데이터 삽입 완료.")

        # 3. 유사 청크 검색 테스트
        print("\n3. 유사 청크 검색 테스트 중...")
        # 첫 번째 청크와 유사한 쿼리 벡터 생성 (약간의 노이즈 추가)
        query_vector = (np.array(chunks_data[0]["embedding"]) + np.random.rand(1536) * 0.01).tolist()
        
        similar_chunks = db_manager.find_similar_chunks(query_vector, k=2)
        
        print(f"검색된 유사 청크 ({len(similar_chunks)}개):")
        for text, similarity in similar_chunks:
            print(f"  - 텍스트: '{text[:50]}...' (유사도/거리: {similarity:.4f})")
        
        if len(similar_chunks) > 0:
            print("유사 청크 검색 테스트 성공.")
        else:
            print("유사 청크 검색 테스트 실패: 결과가 없습니다.")

    except Exception as e:
        print(f"\n❌ 테스트 중 오류 발생: {e}")
        # oracledb.LOB 객체에서 read() 메서드 호출 시 오류가 발생할 수 있으므로,
        # 오류 발생 시 LOB 객체의 타입을 확인하는 디버그 코드 추가
        if isinstance(e, oracledb.Error):
            print(f"Oracle DB Error Code: {e.args[0].code}")
            print(f"Oracle DB Error Message: {e.args[0].message}")
            # 특히 LOB 객체 관련 오류일 경우, LOB 객체의 타입을 확인
            if "ORA-" in str(e) and "LOB" in str(e):
                print("LOB 객체 관련 오류일 가능성이 있습니다. 데이터 조회 시 .read() 호출 여부를 확인하세요.")
        
        # 추가 디버깅: chunk_id_map 생성 부분에서 오류가 발생할 수 있으므로,
        # retrieved_chunks의 각 요소의 타입과 값을 출력
        if 'retrieved_chunks' in locals():
            print("\n--- retrieved_chunks 디버그 정보 ---")
            for i, row in enumerate(retrieved_chunks):
                print(f"Row {i}: ID Type={type(row[0])}, ID Value={row[0]}, Text Type={type(row[1])}, Text Value={row[1]}")
            print("----------------------------------")

    finally:
        if db_manager and db_manager.pool:
            db_manager.close()
            print("데이터베이스 연결 풀 닫힘.")
        print("\n--- FAISS 통합 테스트 종료 ---")

if __name__ == "__main__":
    run_faiss_integration_test()
