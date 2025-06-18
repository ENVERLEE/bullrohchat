# chatbot_service.py
import os
import hashlib
from typing import Dict, Any
from langchain_openai import ChatOpenAI
from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate
from database import OracleManager
from embedder import Embedder

class ChatbotService:
    """ RAG 챗봇의 핵심 로직을 담당하는 서비스 클래스 (비용 최적화 적용) """
    def __init__(self, db_manager: OracleManager, embedder: Embedder):
        if not os.getenv("OPENAI_API_KEY"):
            raise ValueError(".env 파일에 OPENAI_API_KEY가 설정되지 않았습니다.")
        self.db_manager = db_manager
        self.embedder = embedder
        self.llm = ChatOpenAI(model_name="gpt-4o-mini", temperature=0)

    def answer_question(self, question: str) -> str:
        """ 사용자의 질문에 대해 RAG 파이프라인을 거쳐 답변을 생성. 캐싱 로직 포함. """
        # 1. 질문을 해시하여 캐시된 답변이 있는지 확인
        question_hash = hashlib.sha256(question.encode()).hexdigest()
        cached_answer = self.db_manager.get_cached_answer(question_hash)
        if cached_answer:
            print("  - [Cache Hit] 이전에 저장된 답변을 반환합니다.")
            return cached_answer

        print("  - [Cache Miss] 새로운 질문에 대한 답변을 생성합니다.")
        # 2. 업체 정보 조회
        business_info = self.db_manager.get_business_info()
        if not business_info:
            return "업체 정보가 설정되지 않았습니다. 'onboard' 명령을 먼저 실행해주세요."

        # 3. 질문 임베딩
        print("  - 질문을 벡터로 변환하는 중...")
        query_vector = self.embedder.embed_query(question).tolist()

        # 4. 블로그 내용에서 유사 내용 검색 (Vector Search)
        print("  - 블로그 내용에서 유사한 정보 검색 중...")
        similar_chunks = self.db_manager.find_similar_chunks(query_vector, k=3)
        print(f"  - [Debug] 유사 블로그 청크: {similar_chunks}")
        blog_context = "\n\n---\n\n".join([text for text, score in similar_chunks])
        print(f"  - [Debug] 블로그 컨텍스트: {blog_context}")

        # 5. 직접 등록한 FAQ에서 관련 내용 검색
        print("  - FAQ에서 관련 정보 검색 중...")
        faq_context = ""
        for faq in business_info.get('faqs', []):
            if question in faq.get('q', ''):
                faq_context += f"Q: {faq['q']}\nA: {faq['a']}\n"
        
        # 6. LLM에 전달할 최종 컨텍스트 구성
        final_context = f"### 블로그에서 발췌한 정보 ###\n{blog_context}\n\n"
        if faq_context:
            final_context += f"### 자주 묻는 질문(FAQ) ###\n{faq_context}\n\n"
        if business_info.get('marketing_info'):
            final_context += f"### 현재 진행중인 이벤트 및 공지 ###\n{business_info['marketing_info']}\n"
            
        # 7. 동적 프롬프트 생성 및 LLM 호출
        prompt_template = """
# 역할 정의 (Role Definition)
당신은 '{business_name}'의 전문 AI 고객 상담원입니다. 
당신의 전문성: 고객 서비스, 정보 검색, 문제 해결
당신의 성격: {personality}
당신의 목표: 고객 만족도 최대화 및 정확한 정보 제공

# 핵심 지침 (Core Guidelines)
## 정보 처리 원칙
1. **근거 기반 답변**: 오직 제공된 참고 자료만을 근거로 답변
2. **정확성 우선**: 불확실한 정보는 추측하지 않음
3. **투명성 유지**: 정보 부족 시 솔직하게 안내
4. **맥락 고려**: 고객의 의도와 상황을 종합적으로 판단

## 답변 생성 과정 (Step-by-Step Process)
다음 단계를 순서대로 수행하세요:

### 1단계: 질문 분석
- 고객의 핵심 의도 파악
- 필요한 정보 유형 식별
- 긴급도 및 중요도 평가

### 2단계: 자료 검토
- 참고 자료에서 관련 정보 탐색
- 정보의 신뢰도 및 관련성 평가
- 부족한 정보 영역 식별

### 3단계: 답변 구성
- 찾은 정보를 논리적으로 구조화
- {personality} 스타일에 맞게 톤앤매너 조정
- 고객이 이해하기 쉬운 언어로 변환

### 4단계: 품질 검증
- 답변의 정확성 재확인
- 고객의 질문에 직접적으로 대답하는지 점검
- 추가 도움이 필요한 부분 확인

# 상황별 대응 가이드

## 정보가 충분한 경우
**답변 구조:**
```
[간단한 인사] + [핵심 답변] + [부가 설명] + [추가 도움 제안]
```

**예시:**
"안녕하세요! 문의해주신 [주제]에 대해 안내드리겠습니다. 
[구체적 정보 제공]
[추가 설명이나 주의사항]
혹시 더 궁금한 점이 있으시면 언제든 말씀해 주세요."

## 정보가 부족한 경우
**단계적 대응:**
1. 공감과 이해 표현
2. 현재 제공 가능한 관련 정보 안내
3. 대안 제시 (상담 연결, 추후 문의 등)
4. 긍정적 마무리

**예시:**
"고객님의 문의를 충분히 이해했습니다. 
현재 제공된 자료로는 정확한 답변이 어려워 보입니다.
하지만 [관련된 일반적 정보]는 안내드릴 수 있습니다.
더 정확한 정보를 위해 [대안 제시]를 권해드립니다."

# 제약 조건 (Constraints)
## 필수 준수사항
- ✅ 참고 자료 범위 내에서만 답변
- ✅ {personality} 톤앤매너 유지
- ✅ 고객 친화적 언어 사용
- ✅ 단계별 사고 과정 적용

## 금지사항
- ❌ 추측이나 가정에 기반한 답변
- ❌ 참고 자료 외부 정보 사용
- ❌ 부정확하거나 오해의 소지가 있는 표현
- ❌ 고객을 단순히 다른 곳으로 돌리는 답변

# 참고 자료
```
{context}
```

# 고객 질문
```
{question}
```

---

# 답변 생성
위의 모든 지침을 따라 단계별로 사고한 후 최종 답변을 제공하세요.

**사고 과정:** (간단히 요약)
1. 질문 분석: [핵심 의도]
2. 자료 검토: [관련 정보 유무]
3. 답변 구성: [선택한 접근 방식]
4. 품질 검증: [최종 확인 사항]

**최종 답변:**
[여기에 고객을 위한 답변 작성]
        """
        prompt = PromptTemplate(template=prompt_template, input_variables=["business_name", "personality", "context", "question"])
        
        print("  - LLM으로 최종 답변 생성 중...")
        # LangChainDeprecationWarning 해결: LLMChain 대신 prompt | llm 사용
        chain = prompt | self.llm
        response = chain.invoke({
            "business_name": business_info['business_name'],
            "personality": business_info['chatbot_personality'] or "친절하고 명확하게",
            "context": final_context.strip(),
            "question": question
        })
        
        final_answer = response.content
        
        # 8. 생성된 답변을 캐시에 저장
        self.db_manager.cache_answer(question_hash, final_answer)

        return final_answer
