# PROMPTS.md - AI 코딩 툴 프롬프트 로그

**사용 도구:** Claude Code (Anthropic, claude-opus-4-6 모델)

**과제:** StructRAG 논문 오픈소스 코드 구현

**작성일:** 2026-05-06

---

## 1. 과제 파악 및 계획 수립

**프롬프트:**
> StructRAG 논문의 오픈소스 코드를 구현해보려고 하는데, 원본 코드가 GitHub에 공개되어 있지만 72B 모델이랑 GPU 4장이 필요해서 그대로는 못 돌리거든. 내 맥북에서 실행 가능하도록 구현하고 싶은데, 어떤 순서로 진행하면 좋을지 계획을 잡아줘.

**Claude Code 응답 요약:**
- 4단계 계획 수립: (1) 원본 코드 클론 및 구조 파악 (2) Ollama 환경 세팅 (3) 파이프라인 구현 (4) 실행 및 결과 확인
- 제출물: 보고서 + 프롬프트 로그(PROMPTS.md) + 구현 코드(run_demo.py) → GitHub 업로드

---

## 2. 원본 코드 클론 및 구조 파악

**프롬프트:**
> 논문 PDF에 GitHub 링크가 있더라고. 원본 코드를 클론해서 어떤 파일들이 있는지 파악하고, 내가 구현할 때 어떤 부분을 참고해야 하는지 정리해줘.

**Claude Code 수행 작업:**
1. GitHub 레포 클론 (https://github.com/icip-cas/StructRAG)
2. 전체 파일 목록 출력 및 역할 정리

**응답 요약:**
- 핵심 파일 4개: main.py, router.py, structurizer.py, utilizer.py
- LLM API: utils/qwenapi.py (vLLM OpenAI-compatible API 사용 → Ollama로 교체 가능)
- 프롬프트: prompts/ 폴더에 6개 템플릿
- 파이프라인 흐름: Router → Structurizer → Utilizer

---

## 3. 구현 환경 세팅

**프롬프트:**
> 원본 코드가 Qwen2-72B에 GPU 4장이 필요한데, 내 맥북(16GB RAM)에서 돌릴 수 있는 대안이 뭐가 있을까? Ollama가 설치되어 있는데 이걸로 할 수 있어?

**Claude Code 수행 작업:**
1. 시스템 확인: macOS 16GB RAM, Ollama 0.20.2 설치 확인
2. 16GB RAM에 적합한 모델 선정: Qwen2.5-3B (1.9GB)
3. 모델 다운로드: `ollama pull qwen2.5:3b`

**응답 요약:**
- 원본 QwenAPI가 OpenAI-compatible API 형식이고, Ollama도 동일한 형식 제공
- API 엔드포인트만 바꾸면 파이프라인 구조를 그대로 유지 가능
- 72B → 3B로 축소하면 Router 정확도는 떨어지지만, 파이프라인 동작 검증은 가능

---

## 4. OllamaAPI 클래스 구현

**프롬프트:**
> 원본 utils/qwenapi.py를 참고해서 Ollama용 LLM API 래퍼를 구현해줘. 원본은 vLLM 서버에 HTTP POST 요청을 보내는 구조인데, Ollama도 같은 형식이니까 엔드포인트만 바꿔서 구현하면 될 것 같아. 3B 모델이라 컨텍스트 제한도 고려해줘.

**Claude Code 수행 작업:**
- OllamaAPI 클래스 구현: Ollama /v1/chat/completions 엔드포인트로 HTTP POST 요청
- 입력 8000자 초과 시 자동 truncation 처리
- 타임아웃 600초 설정 (CPU 추론 속도 고려)
- 응답 시간 로깅 기능 추가

---

## 5. Router 클래스 구현

**프롬프트:**
> 원본 router.py의 로직을 그대로 구현해줘. 원본은 prompts/route.txt에서 few-shot 프롬프트를 읽는데, 내 구현에서는 프롬프트를 코드 안에 직접 넣어줘. LLM 출력에서 키워드 매칭하는 부분도 원본이랑 동일하게 해줘.

**Claude Code 수행 작업:**
- Router 클래스 구현: 원본 route.txt의 few-shot 프롬프트를 코드 내에 직접 포함
- 키워드 매칭 로직: table > graph > algorithm > catalogue > chunk 우선순위
- 매칭 실패 시 기본값 "chunk" 반환

---

## 6. Structurizer 클래스 구현

**프롬프트:**
> 원본 structurizer.py를 간소화해서 구현해줘. 원본은 중국어 구분자로 문서를 파싱하는데 내 테스트 데이터에선 필요 없으니까 그 부분은 빼고, Table/Graph/Chunk 3가지 구조 변환만 구현해줘. 각각 LLM한테 어떤 프롬프트를 보내는지도 원본 construct_*.txt를 참고해서 만들어줘.

**Claude Code 수행 작업:**
- Structurizer 클래스 구현: construct() 메서드에서 구조 타입별 분기 처리
- Table: LLM에게 관련 테이블 추출 지시
- Graph: LLM에게 head-relation-tail 트리플 추출 지시
- Chunk: LLM 호출 없이 원본 문서 그대로 반환
- 원본의 중국어 구분자 파싱 및 외부 프롬프트 파일 로드 부분 제거

---

## 7. Utilizer 클래스 구현

**프롬프트:**
> 원본 utilizer.py의 3단계 로직(do_decompose, do_extract, do_merge)을 구현해줘. 질문 분해 → 정보 추출 → 답변 생성 흐름을 그대로 유지하되, 프롬프트는 원본 decompose.txt를 참고해서 코드 안에 직접 넣어줘.

**Claude Code 수행 작업:**
- do_decompose(): 복합 질문을 하위 질문으로 분해, LLM 출력을 줄바꿈으로 파싱
- do_extract(): 하위 질문들을 합쳐서 구조화된 지식에서 정보 추출
- do_merge(): 추출 결과를 종합하여 "상세하고 일관된" 최종 답변 생성

---

## 8. 테스트 데이터 생성 및 파이프라인 실행

**프롬프트:**
> 구현한 모듈들을 연결해서 end-to-end로 돌려볼 수 있게 해줘. 테스트 데이터도 3가지 유형(통계 비교 질문, 인용 관계 질문, 단순 QA)으로 만들어서 Router가 각각 다른 구조를 선택하는지 확인하고 싶어.

**Claude Code 수행 작업:**
- create_test_data() 함수: 3가지 유형의 테스트 데이터 생성
  - test_1_table: 회사 A, B, C 매출/이익 비교 (기대: Table)
  - test_2_graph: 논문 간 인용 관계 파악 (기대: Graph)
  - test_3_chunk: StructRAG 논문의 주요 기여 (기대: Chunk)
- run_pipeline() 함수: Step 1~5 순차 실행 + 결과 JSON 저장

**실행 결과:**
| 테스트 | 기대 타입 | 실제 선택 | 소요 시간 |
|--------|-----------|-----------|-----------|
| 매출 비교 (Table) | Table | Chunk | 4.39분 |
| 인용 관계 (Graph) | Graph | Chunk | 5.21분 |
| 단순 QA (Chunk) | Chunk | Chunk | 4.33분 |

**결과 요약:**
- 3B 모델은 모든 질문에 "chunk"를 선택 → Router 정확도는 대형 모델(72B)에 크게 의존
- 인용 관계 질문(test_2)은 chunk 구조에서도 정확히 답변 → 파이프라인 자체는 정상 동작
- CPU 추론 속도 한계로 일부 타임아웃 발생 (120초→600초로 수정하여 해결)

---

## 9. GitHub 업로드

**프롬프트:**
> 구현이 끝났으니까 GitHub 레포(xxunivs/StructRAG)에 보고서, 프롬프트 로그, 구현 코드, 실행 결과를 전부 올려줘.

**Claude Code 수행 작업:**
- 기존 레포 클론 후 PROMPTS.md, run_demo.py, demo_results.json 추가
- git commit & push 완료
