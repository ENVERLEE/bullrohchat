# crawler.py
import re
import time
import json
import requests # Added for direct API calls
from typing import Dict, Any, List, Optional
from tqdm import tqdm # Add this import
from dotenv import load_dotenv
# Import necessary libraries from Selenium for web scraping
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Import BeautifulSoup for parsing HTML content
from bs4 import BeautifulSoup

load_dotenv()

class BlogCrawler:
    """
    A class to crawl all posts from a Naver blog.
    This version is enhanced to use Naver's internal API for fetching post lists,
    and has refined selectors for accurately scraping post content.
    """
    # Define the base URL for Naver Blog PC version.
    BASE_URL_PC = "https://blog.naver.com"

    # [Refined] Define robust CSS selectors for post content details
    CONTENT_SELECTORS = ".se-main-container, .post_content, .se-component.se-text.se-section, .sect_dsc, .post_ct, #content-area .post_content, .se-module-text, .pcol1 .post_content, .se-main-container, .post-view"
    WRITER_SELECTORS = ".nick_name, .blog_author .author_name, .author, .writer, .nickname, .blog_name, .blog_name, .nickname"
    DATE_SELECTORS = ".se_time, .blog_header_info .date, ._postContents .post_info .date, .post_date, .date, .write_date, .se_publishDate, .date"
    HASHTAG_SELECTORS = "div.post_tag a, .se_component_hashtag a"


    def __init__(self, headless: bool = False):
        """
        Initializes the Selenium WebDriver.

        Args:
            headless (bool): If True, runs the browser in headless mode (without a GUI).
        """
        # Set up options for the Chrome WebDriver.
        options = webdriver.ChromeOptions()
        if headless:
            options.add_argument("--headless")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/98.0.4758.102 Safari/537.36")
        
        try:
            # Initialize the Chrome WebDriver for scraping post details.
            self.driver = webdriver.Chrome(options=options)
            print("✅ WebDriver has been successfully initialized.")
        except Exception as e:
            # Handle exceptions during WebDriver setup.
            print(f"❌ WebDriver setup failed: {e}")
            print("  - Please ensure that ChromeDriver is installed and its path is registered in your system's PATH.")
            raise

    def _extract_blog_id(self, blog_url: str) -> Optional[str]:
        """
        Extracts the blog ID from a given Naver Blog URL.
        """
        # This regex is robust for various Naver blog URL formats.
        match = re.search(r'blog\.naver\.com/([a-zA-Z0-9_-]+)', blog_url)
        if match:
            return match.group(1)
        print(f"❌ Could not extract a valid blog ID from the URL: {blog_url}")
        return None

    def get_image_src(self, img_element):
        """
        이미지 요소에서 유효한 src URL을 추출합니다.
        src에 'blur'가 포함된 경우 data-lazy-src를 우선적으로 사용합니다.
        """
        src = img_element.get_attribute('src')
        lazy_src = img_element.get_attribute('data-lazy-src')

        is_blur = False
        if src and 'blur' in src.lower(): # src에 'blur' 문자열이 있는지 확인 (대소문자 무시)
            is_blur = True
            print(f"    - Blur 이미지 감지됨: {src[:60]}...") # 로그 추가

        is_lazy_valid = lazy_src and lazy_src.startswith('http')
        is_src_valid = src and src.startswith('http') and not src.startswith('data:image')

        if is_blur:
            # Blur 이미지일 경우, 유효한 lazy_src가 있다면 그것을 사용
            if is_lazy_valid:
                print(f"    - data-lazy-src 사용: {lazy_src[:60]}...") # 로그 추가
                return lazy_src
            else:
                # Blur 이미지인데 유효한 lazy_src가 없으면, 해당 이미지는 가져오지 않음 (None 반환)
                print(f"    - Blur 이미지지만 유효한 data-lazy-src 없음.") # 로그 추가
                return None
        elif is_src_valid:
            # Blur 이미지가 아니고 src가 유효하면 src를 사용
            return src
        elif is_lazy_valid:
            # src가 유효하지 않거나 없지만 lazy_src가 유효하면 lazy_src 사용
            # (src가 blur가 아니면서 data URI 이거나 아예 없는 경우 등)
            print(f"    - src 부적합, data-lazy-src 사용: {lazy_src[:60]}...") # 로그 추가
            return lazy_src
        else:
            # 어떤 유효한 URL도 찾지 못함
            return None

    def crawl_all_posts(self, blog_url: str, max_posts: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        [Optimized] Retrieves the URL and title of all posts using Naver's internal API.
        This method is now much faster as it no longer uses Selenium for listing posts.

        Args:
            blog_url (str): The URL of the Naver blog.

        Returns:
            List[Dict[str, Any]]: A list of dictionaries, each containing the 'url' and 'title' of a post.
        """
        blog_id = self._extract_blog_id(blog_url)
        if not blog_id:
            return []

        print(f"\n▶️ Collecting all post listings via API... (ID: {blog_id})")
        all_posts_meta = []
        page = 1

        while True:
            # The API endpoint discovered from the Go code. We fetch 30 items per page for efficiency.
            api_url = f"https://blog.naver.com/PostTitleListAsync.naver?blogId={blog_id}&currentPage={page}&countPerPage=30"
            
            try:
                # Make a direct HTTP request.
                response = requests.get(api_url, timeout=10)
                response.raise_for_status()

                # The API returns JSON-like text with single quotes, which is invalid JSON.
                # We replace them with double quotes to parse correctly.
                response_text = response.text.replace("'", '"')
                data = json.loads(response_text)

                post_list = data.get("postList")
                if not post_list:
                    # If postList is empty, we've reached the last page.
                    print(f"  - No more posts found on page {page}. Finishing collection.")
                    break
                
                for post in post_list:
                    # Ensure 'post' is a dictionary before trying to access its keys
                    if not isinstance(post, dict):
                        print(f"  - ⚠️ Skipped non-dictionary item in post list: {post}")
                        continue

                    log_no = post.get("logNo")
                    if log_no:
                        # Construct the full, permanent post URL.
                        post_url = f"{self.BASE_URL_PC}/{blog_id}/{log_no}"
                        all_posts_meta.append({
                            'url': post_url,
                            'title': str(post.get("title", "")).strip() # Ensure title is string before strip
                        })
                        
                        # Check if max_posts limit is reached
                        if max_posts is not None and len(all_posts_meta) >= max_posts:
                            print(f"  - Reached maximum post limit of {max_posts}. Stopping collection.")
                            break # Break from the for loop

                print(f"  - Page {page}: collected {len(post_list)} post metadata items.")
                page += 1
                time.sleep(0.5) # Be respectful to the server

                # If max_posts limit was reached in the inner loop, break from the outer loop too
                if max_posts is not None and len(all_posts_meta) >= max_posts:
                    break

            except requests.RequestException as e:
                print(f"  - ❌ API request failed on page {page}: {e}")
                break
            except json.JSONDecodeError:
                print(f"  - ❌ Failed to parse API response on page {page}.")
                break
        
        print(f"✅ Collected metadata for a total of {len(all_posts_meta)} posts via API.")
        
        # Trim the list to max_posts if it exceeded the limit in the last page
        if max_posts is not None:
            return all_posts_meta[:max_posts]
        return all_posts_meta

    def crawl_post_content(self, post_url: str) -> Dict[str, Any]:
        """
        [UPDATED] Extracts detailed information from a single post URL.
        Uses the new text extraction logic from the markdown crawler.
        
        Args:
            post_url (str): The URL of the blog post.

        Returns:
            Dict[str, Any]: A dictionary containing the post's content, hashtags, writer, and date.
        """
        markdown_output = []  # 마크다운 블록들을 순서대로 저장할 리스트
        
        try:
            print(f"게시물 접속 시도: {post_url}")
            self.driver.get(post_url)
            # 페이지 로딩 및 JS 실행 충분히 대기
            print("페이지 로딩 대기 중...")
            time.sleep(5)

            # --- iframe으로 전환 ---
            try:
                print("iframe으로 전환 시도...")
                WebDriverWait(self.driver, 15).until(
                    EC.frame_to_be_available_and_switch_to_it((By.ID, "mainFrame"))
                )
                print("iframe으로 성공적으로 전환했습니다.")
                time.sleep(1)

                # --- 제목 찾기 ---
                title = "제목 없음"
                try:
                    title_selectors = [
                        '.se-title-text', '.title_text', '.se_title > .se_textView > .se_textarea', '#title_1 > span'
                    ]
                    for selector in title_selectors:
                        try:
                            title_element = WebDriverWait(self.driver, 5).until(
                                EC.visibility_of_element_located((By.CSS_SELECTOR, selector))
                            )
                            if title_element:
                                title = title_element.text.strip()
                                print(f"제목 찾음: {title}")
                                break
                        except (TimeoutException, NoSuchElementException):
                            continue
                    if title == "제목 없음":
                        print("⚠ 제목 요소를 찾지 못했습니다.")

                except Exception as e:
                    print(f"⚠ 제목 추출 중 오류 발생: {e}")
                    title = "제목 추출 오류"

                # --- 본문 내용 순서대로 추출 ---
                try:
                    print("본문 컨텐츠 요소 분석 시작...")
                    # 스마트에디터의 본문 컨테이너 찾기
                    content_container = WebDriverWait(self.driver, 10).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, '.se-main-container'))
                    )
                    print("본문 컨테이너 찾음 (.se-main-container)")

                    # 컨테이너 내의 모든 'se-component' 요소들을 순서대로 가져옴
                    components = content_container.find_elements(By.CSS_SELECTOR, '.se-component')
                    print(f"총 {len(components)}개의 컴포넌트(블록) 발견.")

                    if not components:  # 구버전 에디터 등 다른 구조일 경우 대비
                        print(".se-component 없음. 대체 선택자 시도 (#postViewArea)...")
                        content_container = WebDriverWait(self.driver, 5).until(
                            EC.presence_of_element_located((By.ID, 'postViewArea'))
                        )
                        # 구버전 에디터는 자식 요소 구조가 다를 수 있음 - 단순화된 접근
                        all_children = content_container.find_elements(By.XPATH, "./*")  # 모든 직계 자식
                        print(f"#postViewArea 내 직계 자식 {len(all_children)}개 발견.")
                        components = all_children  # 자식 요소들을 컴포넌트로 간주

                    if not components:
                        print("⚠ 분석할 본문 컴포넌트를 찾지 못했습니다.")

                    processed_components = 0
                    for index, component in enumerate(components):
                        component_processed = False
                        # 1. 텍스트 컴포넌트인지 확인 (내부에 텍스트 요소 찾기)
                        try:
                            # .se-text-paragraph 클래스를 가진 모든 하위 p 태그 찾기
                            text_paragraphs = component.find_elements(By.CSS_SELECTOR, '.se-text-paragraph')
                            if text_paragraphs:
                                component_text = []
                                for p in text_paragraphs:
                                    paragraph_text = p.text.strip()
                                    if paragraph_text:  # 빈 줄은 제외
                                        component_text.append(paragraph_text)

                                if component_text:  # 추출된 텍스트가 있으면
                                    markdown_output.append("\n".join(component_text))
                                    print(f"  [{index+1}] 텍스트 블록 처리됨: '{component_text[0][:30]}...'")
                                    component_processed = True

                        except NoSuchElementException:
                            pass  # 텍스트 요소 없으면 다음 확인으로

                        # 2. 이미지 컴포넌트인지 확인 (내부에 이미지 요소 찾기)
                        if not component_processed:  # 텍스트가 아니었다면 이미지 확인
                            try:
                                images = component.find_elements(By.TAG_NAME, 'img')
                                if images:
                                    for img in images:
                                        img_src = self.get_image_src(img)  # 정의된 함수 사용
                                        if img_src:
                                            # 이미지 URL을 마크다운 출력에 추가 (실제 다운로드는 하지 않음)
                                            # markdown_output.append(f"[IMAGE: {img_src}]")
                                            print(f"  [{index+1}] 이미지 블록 처리됨: {img_src[:60]}...")
                                            component_processed = True

                            except NoSuchElementException:
                                pass  # 이미지 요소 없으면 다음 확인으로

                        # 3. 기타 컴포넌트 (스티커 등) - 현재는 무시
                        if not component_processed:
                            print(f"  [{index+1}] 처리되지 않은 컴포넌트 (텍스트/이미지 아님)")
                            pass  # 필요시 다른 종류의 컴포넌트 처리 로직 추가

                        processed_components += 1

                    print(f"총 {processed_components}개 컴포넌트 분석 완료.")

                except (TimeoutException, NoSuchElementException):
                    print("⚠ 본문 컨테이너(.se-main-container 또는 #postViewArea)를 찾지 못했습니다.")
                except Exception as e:
                    print(f"⚠ 본문 내용 처리 중 오류 발생: {e}")

                # BeautifulSoup으로 메타데이터 추출 (기존 로직 유지)
                soup = BeautifulSoup(self.driver.page_source, 'html.parser')
                
                # Extract hashtags with improved selectors.
                hashtags = [tag.text.strip().lstrip('#') for tag in soup.select(self.HASHTAG_SELECTORS)]
                
                # Extract additional metadata with improved selectors.
                writer_element = soup.select_one(self.WRITER_SELECTORS)
                date_element = soup.select_one(self.DATE_SELECTORS)
                writer = writer_element.text.strip() if writer_element else "Unknown"
                write_date = date_element.text.strip() if date_element else "Unknown"

                # iframe에서 빠져나오기
                self.driver.switch_to.default_content()
                print("기본 컨텐츠로 돌아왔습니다.")

            except TimeoutException:
                print("⚠ mainFrame iframe을 찾거나 전환하는 데 실패했습니다.")
                markdown_output.append("[오류: iframe을 찾을 수 없습니다.]")
                title = "iframe 오류"
                hashtags = []
                writer = "Unknown"
                write_date = "Unknown"
            except Exception as e:
                print(f"⚠ iframe 처리 중 오류 발생: {e}")
                markdown_output.append(f"[오류: iframe 처리 중 문제 발생 - {e}]")
                title = "처리 오류"
                hashtags = []
                writer = "Unknown"
                write_date = "Unknown"

        except TimeoutException:
            print("⚠ 페이지 로딩 시간 초과.")
            return {}
        except Exception as e:
            print(f"⚠ 크롤링 중 예상치 못한 오류 발생: {e}")
            return {}

        # 최종 컨텐츠 생성
        final_content = "\n\n".join(filter(None, markdown_output))
        
        if not final_content.strip():
            print("⚠ 유효한 컨텐츠를 추출하지 못했습니다.")
            final_content = "[컨텐츠 추출 실패]"
        
        # 서버 부하를 줄이기 위해 요청 사이에 지연 추가
        time.sleep(1) 

        return {
            'title': title,
            'content': final_content,
            'hashtags': hashtags,
            'writer': writer,
            'write_date': write_date,
        }

    def close(self):
        """
        Closes the WebDriver and releases all associated resources.
        """
        if self.driver:
            self.driver.quit()
            print("✅ WebDriver has been closed.")


if __name__ == "__main__":
    # The URL of the blog to be crawled.
    BLOG_URL = "https://blog.naver.com/kokos012"
    crawler = BlogCrawler(headless=True)
    MAX_POSTS_TO_CRAWL = 10 # 크롤링할 최대 포스트 개수 지정

    try:
        # Step 1: Crawl all post URLs and titles using the fast API method.
        all_posts = crawler.crawl_all_posts(BLOG_URL, max_posts=MAX_POSTS_TO_CRAWL)

        if all_posts:
            # Step 2: Crawl the content of the first N posts as a sample.
            print(f"\n--- Crawling content of {len(all_posts)} posts ---")
            for i, post_meta in enumerate(all_posts):
                print(f"\n[{i+1}/{len(all_posts)}] Crawling \"{post_meta['title']}\"...")
                
                # Get the rich content data for the post.
                content_data = crawler.crawl_post_content(post_meta['url'])
                
                if content_data:
                    # Print the enhanced results.
                    print(f"  - Title: {content_data.get('title')}")
                    print(f"  - Writer: {content_data.get('writer')}")
                    print(f"  - Date: {content_data.get('write_date')}")
                    print(f"  - Hashtags: {content_data.get('hashtags')}")
                    content_preview = content_data.get('content', '')[:200].replace(chr(8203), '') # Show more preview
                    print(f"  - Content (first 200 chars): {content_preview}...")
        else:
            print("\n⚠️ No posts were found to crawl.")

    except Exception as e:
        # Catch any exceptions that occur during the main execution.
        print(f"🔴 An error occurred in the main program: {e}")
    finally:
        # Ensure the WebDriver is always closed.
        crawler.close()
