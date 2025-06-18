# main.py
import os
import argparse
import hashlib
from dotenv import load_dotenv
from tqdm import tqdm
import oracledb
import urllib.parse # Add this import
import json
import numpy as np # Add this import
from database import OracleManager
from crawler import BlogCrawler
from embedder import Embedder
from chatbot_service import ChatbotService

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def onboard_command():
    clear_screen(); print("="*50 + "\n       <불로챗> AI 챗봇 온보딩을 시작합니다.\n" + "="*50)
    db = OracleManager()
    existing_info = db.get_business_info()
    if existing_info:
        print("\n[알림] 기존에 저장된 정보가 있습니다. 내용을 수정합니다.")
        default_name = existing_info.get('business_name', '')
        default_url = existing_info.get('blog_url', '')
    else:
        print("\n[안내] 업체 정보와 챗봇 설정을 위해 몇 가지 질문에 답변해주세요.")
        default_name, default_url = "", ""
    business_name = input(f"\n1. 업체 이름을 입력하세요 (기본값: {default_name}): ") or default_name
    blog_url = input(f"2. 정보 기반이 될 네이버 블로그 URL을 입력하세요 (기본값: {default_url}): ") or default_url
    chatbot_personality = input("3. 챗봇의 성격을 설정해주세요 (예: 친절하고 상냥하게): ")
    faqs = []
    print("\n4. 자주 묻는 질문(FAQ)을 추가합니다 (완료 시 그냥 Enter).")
    while True:
        q = input("  - 질문(Q): ");
        if not q: break
        a = input(f"  - 답변(A) for '{q}': "); faqs.append({'q': q, 'a': a})
    marketing_info = input("\n5. 현재 진행중인 이벤트나 마케팅 문구가 있나요? ")
    info = {'business_name': business_name, 'blog_url': blog_url, 'chatbot_personality': chatbot_personality, 'faqs': faqs, 'marketing_info': marketing_info}
    db.save_business_info(info); db.close()
    print("\n" + "="*50 + "\n🎉 온보딩이 완료되었습니다!\n" + "="*50)

def crawl_command(args):
    db = OracleManager()
    info = db.get_business_info()
    if not info or not info.get('blog_url'):
        print("❌ 블로그 URL이 설정되지 않았습니다. 'onboard' 명령을 먼저 실행해주세요."); db.close(); return
    print(f"▶️ '{info['business_name']}'의 블로그({info['blog_url']}) 크롤링을 시작합니다.");
    crawler = BlogCrawler(); embedder = Embedder()
    
    # max_posts 인자를 전달합니다.
    max_posts_to_crawl = args.max_posts if hasattr(args, 'max_posts') else None
    all_posts_meta = crawler.crawl_all_posts(info['blog_url'], max_posts=max_posts_to_crawl)
    
    if not all_posts_meta:
        print("⚠️ 크롤링할 게시글이 없습니다."); crawler.close(); db.close(); return
        
    for post_meta in tqdm(all_posts_meta, desc="게시글 처리 중"):
        # URL 디코딩된 제목을 사용합니다.
        decoded_title = urllib.parse.unquote(post_meta['title'])
        try:
            content_data = crawler.crawl_post_content(post_meta['url'])
            if not content_data:
                tqdm.write(f"  - 콘텐츠 없음: '{decoded_title}' 건너뜁니다.")
                continue

            # content_data가 딕셔너리이므로 JSON 문자열로 변환하여 인코딩합니다.
            # 이전에 'dict' object has no attribute 'encode' 오류가 발생한 부분입니다.
            content_text_for_hash = json.dumps(content_data, ensure_ascii=False)
            new_hash = hashlib.sha256(content_text_for_hash.encode('utf-8')).hexdigest()
            old_hash = db.get_post_hash(post_meta['url'])
            
            # 임베딩을 위해 실제 텍스트 콘텐츠를 사용합니다.
            content_for_embedding = content_data.get('content', '')

            if new_hash == old_hash:
                tqdm.write(f"  - [변경 없음] '{decoded_title}' 건너뜁니다.")
                continue
            
            tqdm.write(f"  - [콘텐츠 변경 감지] '{decoded_title}' 처리 시작...")
            chunks = embedder.split_text(content_for_embedding)
            embeddings = embedder.embed_texts(chunks) # <- 변경된 경우에만 API 호출
            # embeddings는 이미 리스트의 리스트이므로, .tolist()를 다시 호출할 필요가 없습니다.
            chunks_with_embeddings = [{"chunk_text": text, "embedding": emb} for text, emb in zip(chunks, embeddings)]
            db.upsert_post_with_chunks(post_meta['url'], post_meta['title'], new_hash, chunks_with_embeddings)
        except Exception as e:
            tqdm.write(f"  - ❌ 처리 중 오류 발생: {post_meta['url']}, {e}")
            
    crawler.close(); db.close()
    print("\n🎉 블로그 전체 데이터화 작업이 완료되었습니다.")

def ask_command(question: str):
    db = OracleManager(); embedder = Embedder()
    chatbot = ChatbotService(db, embedder)
    print("\n🤔 AI 챗봇이 답변을 생성하고 있습니다...")
    answer = chatbot.answer_question(question)
    print("\n" + "="*50 + f"\n👤 고객 질문: {question}\n" + " ="*50)
    print(f"\n🤖 <불로챗> 답변:\n\n{answer}\n\n" + "="*50)
    db.close()

def main():
    load_dotenv()
    parser = argparse.ArgumentParser(description="<불로챗> 소상공인 AI 챗봇 자동화 플랫폼 (비용 최적화 버전)")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("onboard", help="대화형으로 챗봇 설정을 시작합니다.")
    subparsers.add_parser("setup-db", help="Oracle DB에 테이블과 인덱스를 생성합니다.")
    crawl_parser = subparsers.add_parser("crawl", help="블로그 게시글을 크롤링하고 변경된 내용만 DB에 반영합니다.")
    crawl_parser.add_argument("--max-posts", type=int, default=None, help="크롤링할 최대 게시글 수 (기본값: 모든 게시글)")
    ask_parser = subparsers.add_parser("ask", help="챗봇에게 질문합니다 (답변 캐싱 기능 포함).")
    ask_parser.add_argument("question", type=str, help="AI에게 할 질문")
    args = parser.parse_args()
    try:
        if args.command == "setup-db":
            db = OracleManager()
            db.reset_database() # setup_tables 대신 reset_database 호출
            db.close()
        elif args.command == "onboard":
            onboard_command()
        elif args.command == "crawl":
            crawl_command(args)
        elif args.command == "ask":
            ask_command(args.question)
    except oracledb.Error as e:
        print(f"\n❌ 데이터베이스 오류: {e}\n  - .env 파일 및 Oracle Cloud ATP 설정을 확인해주세요.")
    except ValueError as e:
        print(f"\n❌ 설정 오류: {e}")
    except Exception as e:
        print(f"\n❌ 예기치 않은 오류: {e}")

if __name__ == "__main__":
    main()
