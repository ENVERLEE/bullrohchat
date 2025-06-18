# reset_database.py
import oracledb
from dotenv import load_dotenv
from database import OracleManager

def reset_database():
    """
    데이터베이스의 모든 테이블을 삭제하고 다시 생성하여 초기화합니다.
    """
    load_dotenv()
    db_manager = None
    try:
        print("🔄 데이터베이스 초기화를 시작합니다...")
        db_manager = OracleManager()

        # 테이블 목록 (외래 키 제약 조건을 고려하여 삭제 순서 중요)
        tables_to_drop = ['qa_cache', 'chunks', 'posts', 'business_info']
        
        with db_manager.pool.acquire() as connection:
            with connection.cursor() as cursor:
                for table_name in tables_to_drop:
                    try:
                        # 인덱스가 테이블과 함께 자동으로 삭제되므로 별도 삭제 불필요
                        sql = f"DROP TABLE {table_name} PURGE"
                        cursor.execute(sql)
                        print(f"  - '{table_name}' 테이블을 성공적으로 삭제했습니다.")
                    except oracledb.Error as e:
                        # ORA-00942: table or view does not exist
                        if "ORA-00942" in str(e):
                            print(f"  - '{table_name}' 테이블이 이미 존재하지 않아 건너뜁니다.")
                        else:
                            print(f"  - '{table_name}' 테이블 삭제 중 오류 발생: {e}")
                            # 오류가 발생해도 계속 진행
                            
        print("\n🔧 모든 기존 테이블 삭제 완료. 테이블 재생성을 시작합니다...")
        
        # 테이블 재생성
        db_manager.setup_tables()
        
        print("\n✅ 데이터베이스 초기화가 성공적으로 완료되었습니다.")

    except Exception as e:
        print(f"❌ 데이터베이스 초기화 중 심각한 오류 발생: {e}")
    finally:
        if db_manager:
            db_manager.close()

if __name__ == "__main__":
    # 사용자가 직접 실행했을 때만 초기화 진행
    confirm = input("정말로 데이터베이스를 초기화하시겠습니까? 모든 데이터가 삭제됩니다. (y/n): ")
    if confirm.lower() == 'y':
        reset_database()
    else:
        print("데이터베이스 초기화가 취소되었습니다.")
