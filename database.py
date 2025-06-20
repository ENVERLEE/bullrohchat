import os
import json
import oracledb
import numpy as np
oracledb.init_oracle_client()
print(f"DEBUG: oracledb module loaded from: {oracledb.__file__}")
print(f"DEBUG: oracledb version: {oracledb.__version__}")
from typing import List, Dict, Any, Tuple, Optional

class OracleManager:
    def __init__(self):
        try:
            self.user = os.getenv("ORACLE_USER")
            self.password = os.getenv("ORACLE_PASSWORD")
            self.dsn = os.getenv("ORACLE_ATP_DSN")
            self.wallet_path = os.getenv("ORACLE_WALLET_PATH")
            self.wallet_password = os.getenv("ORACLE_WALLET_PASSWORD")

            if not all([self.user, self.password, self.dsn, self.wallet_path, self.wallet_password]):
                raise ValueError(".env 파일에 Oracle Cloud ATP 접속 정보가 모두 설정되었는지 확인해주세요.")

            self.pool = oracledb.create_pool(
                user=self.user, password=self.password, dsn=self.dsn,
                config_dir=self.wallet_path, wallet_location=self.wallet_path,
                wallet_password=self.wallet_password, min=2, max=5, increment=1
            )
            print("✅ Oracle Cloud ATP 연결 풀 생성 완료.")

            self.embedding_dim = 1536 # 임베딩 벡터 차원 (OpenAI text-embedding-ada-002 기준)

        except oracledb.Error as e:
            print(f"❌ Oracle DB 연결 풀 생성 실패: {e}")
            raise

    def _get_connection(self):
        return self.pool.acquire()

    def _execute_sql(self, sql: str, params: dict = None, commit: bool = False):
        with self.pool.acquire() as connection:
            with connection.cursor() as cursor:
                cursor.execute(sql, params or {})
                if commit:
                    connection.commit()
                else:
                    try: 
                        rows = cursor.fetchall()
                        # LOB 객체를 문자열로 변환
                        processed_rows = []
                        for row in rows:
                            processed_row = []
                            for item in row:
                                if isinstance(item, oracledb.LOB):
                                    processed_row.append(item.read())
                                else:
                                    processed_row.append(item)
                            processed_rows.append(tuple(processed_row))
                        return processed_rows
                    except oracledb.Error: return None

    def _execute_many(self, sql: str, params_list: List[Dict]):
        with self.pool.acquire() as connection:
            with connection.cursor() as cursor:
                cursor.executemany(sql, params_list, batcherrors=True)
                for error in cursor.getbatcherrors():
                    print(f"DB Error: {error.message} at row offset {error.offset}")
                connection.commit()

    def setup_tables(self):
        print("🔍 데이터베이스 스키마 설정 시작...")
        
        # BUSINESS_INFO 테이블
        try:
            business_sql = """
            CREATE TABLE business_info (
                id NUMBER(1) DEFAULT 1 NOT NULL,
                business_name NVARCHAR2(100) NOT NULL,
                blog_url VARCHAR2(1024),
                chatbot_personality NVARCHAR2(500),
                faqs NCLOB,
                marketing_info NCLOB,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                CONSTRAINT business_info_pk PRIMARY KEY (id),
                CONSTRAINT single_row_check CHECK (id = 1)
            )
            """
            self._execute_sql(business_sql, commit=True)
            print("  - 'business_info' 테이블 생성 완료.")
        except oracledb.Error as e:
            if "ORA-00955" in str(e): 
                print("  - 'business_info' 테이블이 이미 존재합니다.")
            else: 
                print(f"  - business_info 테이블 생성 오류: {e}")
                raise

        # POSTS 테이블
        try:
            posts_sql = """
            CREATE TABLE posts (
                id NUMBER GENERATED BY DEFAULT AS IDENTITY,
                post_url VARCHAR2(1024) NOT NULL,
                title NVARCHAR2(512),
                content_hash VARCHAR2(64),
                crawled_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                CONSTRAINT posts_pk PRIMARY KEY (id),
                CONSTRAINT posts_url_uk UNIQUE (post_url)
            )
            """
            self._execute_sql(posts_sql, commit=True)
            print("  - 'posts' 테이블 생성 완료.")
        except oracledb.Error as e:
            if "ORA-00955" in str(e): 
                print("  - 'posts' 테이블이 이미 존재합니다.")
            else: 
                print(f"  - posts 테이블 생성 오류: {e}")
                raise
        
        # CHUNKS 테이블 (FAISS 인덱스 파일 경로 저장)
        try:
            chunks_sql = """
            CREATE TABLE chunks (
                id NUMBER GENERATED BY DEFAULT AS IDENTITY,
                post_id NUMBER NOT NULL,
                chunk_text NCLOB,
                chunk_vector NCLOB, -- Oracle AI Vector Search를 위한 벡터 임베딩 저장 (문자열로 저장)
                CONSTRAINT chunks_pk PRIMARY KEY (id),
                CONSTRAINT fk_post FOREIGN KEY (post_id) REFERENCES posts (id) ON DELETE CASCADE
            )
            """
            self._execute_sql(chunks_sql, commit=True)
            print("  - 'chunks' 테이블 생성 완료 (FAISS 경로 저장용).")
        except oracledb.Error as e:
            if "ORA-00955" in str(e): 
                print("  - 'chunks' 테이블이 이미 존재합니다.")
            else: 
                print(f"  - chunks 테이블 생성 오류: {e}")
                raise

        # QA_CACHE 테이블
        try:
            cache_sql = """
            CREATE TABLE qa_cache (
                question_hash VARCHAR2(64),
                answer NCLOB NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                CONSTRAINT qa_cache_pk PRIMARY KEY (question_hash)
            )
            """
            self._execute_sql(cache_sql, commit=True)
            print("  - 'qa_cache' 테이블 생성 완료.")
        except oracledb.Error as e:
            if "ORA-00955" in str(e): 
                print("  - 'qa_cache' 테이블이 이미 존재합니다.")
            else: 
                print(f"  - qa_cache 테이블 생성 오류: {e}")
                raise

        # USERS 테이블
        try:
            users_sql = """
            CREATE TABLE users (
                id NUMBER GENERATED BY DEFAULT AS IDENTITY,
                username NVARCHAR2(50) NOT NULL UNIQUE,
                email NVARCHAR2(100) NOT NULL UNIQUE,
                password NVARCHAR2(255) NOT NULL,
                is_premium NUMBER(1,0) DEFAULT 0 NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                CONSTRAINT users_pk PRIMARY KEY (id)
            )
            """
            self._execute_sql(users_sql, commit=True)
            print("  - 'users' 테이블 생성 완료.")
        except oracledb.Error as e:
            if "ORA-00955" in str(e): 
                print("  - 'users' 테이블이 이미 존재합니다.")
            else: 
                print(f"  - users 테이블 생성 오류: {e}")
                raise
                
        print("✅ 데이터베이스 스키마 설정이 완료되었습니다.")

    def _drop_table_if_exists(self, table_name: str):
        try:
            self._execute_sql(f"DROP TABLE {table_name} CASCADE CONSTRAINTS", commit=True)
            print(f"  - '{table_name}' 테이블 삭제 완료.")
        except oracledb.Error as e:
            if "ORA-00942" in str(e):
                print(f"  - '{table_name}' 테이블이 존재하지 않습니다.")
            else:
                print(f"  - '{table_name}' 테이블 삭제 오류: {e}")
                raise

    def reset_database(self):
        print("🚨 데이터베이스 초기화 시작...")
        # 테이블 삭제 (의존성 역순으로)
        self._drop_table_if_exists("qa_cache")
        self._drop_table_if_exists("chunks")
        self._drop_table_if_exists("posts")
        self._drop_table_if_exists("business_info")
        self._drop_table_if_exists("users")
        
        # 테이블 다시 생성
        self.setup_tables()
        print("✅ 데이터베이스 초기화 및 재설정 완료.")

    def get_user_by_id(self, user_id):
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT id, username, email, password, NVL(is_premium, 0) FROM users WHERE id = :id", [user_id])
                row = cur.fetchone()
        
        if row:
            return {'id': row[0], 'username': row[1], 'email': row[2], 'password': row[3], 'is_premium': row[4]}
        return None

    def get_user_by_username(self, username):
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT id, username, email, password, NVL(is_premium, 0) FROM users WHERE username = :username", [username])
                row = cur.fetchone()
        
        if row:
            return {'id': row[0], 'username': row[1], 'email': row[2], 'password': row[3], 'is_premium': row[4]}
        return None

    def create_user(self, username, email, hashed_password):
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("INSERT INTO users (username, email, password, is_premium) VALUES (:username, :email, :password, 0)", [username, email, hashed_password])
                conn.commit()

    def upgrade_user_to_premium(self, user_id):
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("UPDATE users SET is_premium=1 WHERE id=:id", [user_id])
                conn.commit()

    def get_post_hash(self, post_url: str) -> Optional[str]:
        sql = "SELECT content_hash FROM posts WHERE post_url = :url"
        result = self._execute_sql(sql, {'url': post_url})
        return result[0][0] if result and result[0][0] else None

    def upsert_post_with_chunks(self, post_url: str, title: str, content_hash: str, chunks_data: List[Dict[str, Any]]):
        # 기존 데이터 삭제
        delete_sql = """
        BEGIN 
            DELETE FROM chunks WHERE post_id IN (SELECT id FROM posts WHERE post_url = :url); 
            DELETE FROM posts WHERE post_url = :url; 
        END;
        """
        self._execute_sql(delete_sql, {'url': post_url}, commit=True)
        
        # 새 게시글 삽입
        insert_post_sql = """
        INSERT INTO posts (post_url, title, content_hash) 
        VALUES (:post_url, :title, :hash) 
        RETURNING id INTO :post_id
        """
        with self.pool.acquire() as conn, conn.cursor() as cursor:
            post_id_var = cursor.var(oracledb.DB_TYPE_NUMBER)
            cursor.execute(insert_post_sql, {
                'post_url': post_url, 
                'title': title, 
                'hash': content_hash, 
                'post_id': post_id_var
            })
            post_id = post_id_var.getvalue()[0]
            conn.commit()
        # 청크 데이터 저장
        if chunks_data:
            insert_chunks_sql = """
            INSERT INTO chunks (post_id, chunk_text, chunk_vector) 
            VALUES (:post_id, :chunk_text, :chunk_vector)
            """
            with self.pool.acquire() as conn, conn.cursor() as cursor:
                for chunk in chunks_data:
                    params = {
                        'post_id': post_id, 
                        'chunk_text': chunk['chunk_text'], 
                        'chunk_vector': json.dumps(chunk['embedding'].tolist()) # JSON 형식으로 저장
                    }
                    cursor.execute(insert_chunks_sql, params)
                conn.commit()
        
        print(f"  > 게시글 '{title}' 및 {len(chunks_data)}개 청크 저장 완료.")

    def get_cached_answer(self, question_hash: str) -> Optional[str]:
        sql = "SELECT answer FROM qa_cache WHERE question_hash = :hash"
        result = self._execute_sql(sql, {'hash': question_hash})
        return result[0][0] if result and result[0][0] else None
    
    def cache_answer(self, question_hash: str, answer: str):
        sql = "INSERT INTO qa_cache (question_hash, answer) VALUES (:hash, :answer)"
        self._execute_sql(sql, {'hash': question_hash, 'answer': answer}, commit=True)
        print("  - 새로운 답변을 캐시에 저장했습니다.")

    def save_business_info(self, info: Dict[str, Any]):
        sql = """
        MERGE INTO business_info dest 
        USING (SELECT 1 AS id FROM dual) src 
        ON (dest.id = src.id)
        WHEN MATCHED THEN 
            UPDATE SET 
                business_name = :name, 
                blog_url = :url, 
                chatbot_personality = :personality, 
                faqs = :faqs, 
                marketing_info = :marketing, 
                last_updated = CURRENT_TIMESTAMP
        WHEN NOT MATCHED THEN 
            INSERT (id, business_name, blog_url, chatbot_personality, faqs, marketing_info) 
            VALUES (1, :name, :url, :personality, :faqs, :marketing)
        """
        params = {
            'name': info['business_name'], 
            'url': info['blog_url'], 
            'personality': info['chatbot_personality'], 
            'faqs': json.dumps(info['faqs'], ensure_ascii=False), 
            'marketing': info['marketing_info']
        }
        self._execute_sql(sql, params, commit=True)
        print("✅ 업체 정보가 데이터베이스에 저장되었습니다.")

    def get_business_info(self) -> Optional[Dict[str, Any]]:
        sql = "SELECT business_name, blog_url, chatbot_personality, faqs, marketing_info FROM business_info WHERE id = 1"
        result = self._execute_sql(sql)
        if not result: 
            return None
        
        row = result[0]
        faqs_json = row[3] if row[3] else '[]'
        marketing_text = row[4] if row[4] else ''
        
        return {
            'business_name': row[0], 
            'blog_url': row[1], 
            'chatbot_personality': row[2], 
            'faqs': json.loads(faqs_json), 
            'marketing_info': marketing_text
        }

    def find_similar_chunks(self, query_vector: list, k: int = 5) -> List[Tuple[str, float]]:
        # 모든 청크 데이터를 가져와 Python에서 유사도 계산
        sql = "SELECT chunk_text, chunk_vector FROM chunks"
        results = self._execute_sql(sql)
        print(f"  - [Debug] chunks 테이블에서 {len(results) if results else 0}개의 청크를 가져왔습니다.")

        query_np_vector = np.array(query_vector)
        similarities = []

        if results:
            for row in results:
                chunk_text = row[0] if hasattr(row[0], 'read') else row[0]
                chunk_vector_str = row[1] if hasattr(row[1], 'read') else row[1]
                
                try:
                    # 문자열 형태의 벡터를 NumPy 배열로 변환
                    chunk_np_vector = np.array(json.loads(chunk_vector_str))
                    
                    # L2 Distance (유클리드 거리) 계산
                    distance = np.linalg.norm(query_np_vector - chunk_np_vector)
                    similarities.append((chunk_text, distance))
                except json.JSONDecodeError as e:
                    print(f"❌ 벡터 문자열 파싱 오류: {e} - {chunk_vector_str[:100]}...") # 오류나는 문자열 일부 출력
                    continue
                except Exception as e:
                    print(f"❌ 유사도 계산 중 예기치 않은 오류: {e}")
                    continue
        
        # 거리가 짧은 순서대로 정렬하고 상위 k개 반환
        similarities.sort(key=lambda x: x[1])
        return similarities[:k]

    def close(self):
        if self.pool: 
            self.pool.close()
            print("🔌 Oracle Cloud ATP 연결 풀을 닫았습니다.")
