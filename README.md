# 불로챗 (Bullroh Chat)

불로챗은 블로그 콘텐츠를 기반으로 한 AI 챗봇 서비스입니다. 이제 웹 인터페이스를 통해 쉽게 사용할 수 있습니다.

## 기능

- 블로그 크롤링을 통한 자동 학습
- 자연어 기반 질의응답
- 웹 기반 사용자 인터페이스
- 실시간 채팅 기능

## 설치 방법

1. 저장소를 클론합니다:
   ```bash
   git clone [저장소 URL]
   cd bullrohchat
   ```

2. 가상 환경을 생성하고 활성화합니다:
   ```bash
   # Windows
   python -m venv venv
   .\venv\Scripts\activate
   
   # macOS/Linux
   python3 -m venv venv
   source venv/bin/activate
   ```

3. 필요한 패키지를 설치합니다:
   ```bash
   pip install -r requirements.txt
   ```

4. 환경 변수 설정 (`.env` 파일 생성):
   ```
   OPENAI_API_KEY=your_openai_api_key
   # 기타 필요한 환경 변수들
   ```

## 웹 인터페이스 사용 방법

1. 웹 애플리케이션을 실행합니다:
   ```bash
   python web_app.py
   ```

2. 웹 브라우저에서 다음 주소로 접속합니다:
   ```
   http://localhost:5000
   ```

3. 웹 인터페이스에서 다음을 수행할 수 있습니다:
   - 챗봇 시작/중지
   - 실시간 채팅
   - 대화 내역 확인

## 기존 CLI 명령어 사용

기존 CLI 명령어는 그대로 사용 가능합니다:

```bash
# 온보딩 (초기 설정)
python main.py onboard

# 블로그 크롤링
python main.py crawl

# CLI에서 질문하기
python main.py ask "질문 내용"
```

## 라이선스

이 프로젝트는 [라이선스 유형] 라이선스 하에 있습니다.
