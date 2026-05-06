# PROMPTS.md - AI 코딩 툴 프롬프트 로그

**사용 도구:** Claude Code (Anthropic, claude-opus-4-6 모델)

**과제:** StructRAG 논문 오픈소스 코드 구현

**작성일:** 2026-05-06

---

## 1. 과제 파악 및 계획 수립

**프롬프트:**
> StructRAG 논문의 오픈소스 코드를 구현해보려고 하는데, 논문 PDF는 Desktop/수업/캡디1/논문에 있어. 원본 코드가 GitHub에 공개되어 있는데, 72B 모델이랑 GPU 4장이 필요해서 그대로는 못 돌리거든. 내 맥북에서 실행 가능하도록 구현하고 싶은데, 어떤 순서로 진행하면 좋을지 계획을 잡아줘.

**Claude Code 응답 요약:**
- 과제 구조를 정리: 논문의 StructRAG 파이프라인을 로컬 환경에서 실행 가능하도록 구현하고, 그 과정의 프롬프트를 PROMPTS.md에 기록
- 4단계 계획 수립: (1) 원본 코드 구조 파악 (2) 핵심 모듈 분석 (3) 로컬 환경 구현 (4) 실행 및 결과 확인
- 제출물: 보고서 + 프롬프트 로그(PROMPTS.md) + 구현 코드(run_demo.py) → GitHub 업로드

---

## 2. 원본 오픈소스 코드 탐색

**프롬프트:**
> 논문 PDF를 보니까 Abstract 아래에 GitHub 링크가 있더라고. 구현하기 전에 원본 코드를 먼저 클론해서 전체 구조를 파악하고 싶어. 어떤 파일들이 있고, 각 파일이 뭘 하는 건지 정리해줘. 내가 구현할 때 어떤 부분을 참고해야 하는지 알아야 하니까.

**Claude Code 수행 작업:**
1. 웹 검색으로 GitHub 레포 확인: https://github.com/icip-cas/StructRAG
2. 논문 PDF에서도 GitHub 링크 확인 (https://github.com/Li-Z-Q/StructRAG, 현재 icip-cas 조직으로 이전됨)
3. 레포 클론 후 전체 파일 목록 출력

**응답 요약:**
```
StructRAG/
├── main.py              # 파이프라인 진입점
├── router.py            # 구조 타입 선택 모듈
├── structurizer.py      # 문서 구조화 모듈
├── utilizer.py          # 구조화 지식 활용 모듈
├── utils/qwenapi.py     # LLM API 래퍼
├── prompts/             # 프롬프트 템플릿 6개
├── train_router/        # Router DPO 학습 코드
└── Loong/               # 평가 벤치마크
```

---

## 3. 모듈별 코드 분석 (구현 전 사전 분석)

### 3.1 main.py 분석

**프롬프트:**
> main.py가 전체 파이프라인의 진입점인 것 같은데, 코드를 읽어보니 Router, Structurizer, Utilizer를 순서대로 호출하는 구조더라고. 내가 이걸 재구현하려면 이 흐름을 정확히 이해해야 하는데, 전체 실행 흐름이랑 worker_id, start_bias 같은 인자들이 뭘 위한 건지 분석해줘.

**Claude Code 응답 요약:**
- `main.py`는 CLI 인자로 LLM API 서버 URL, 워커 ID 등을 받음
- QwenAPI 클래스로 vLLM 서버에 연결
- Loong 벤치마크 데이터를 로드하여 200개씩 분할 처리 (worker_id로 병렬화)
- 핵심 파이프라인: Router → Structurizer → Utilizer 순으로 실행
- 구현 시 핵심은 이 3단계 파이프라인 흐름을 유지하는 것

### 3.2 router.py 분석

**프롬프트:**
> 논문에서 Hybrid Structure Router가 핵심이라고 하는데, router.py를 보면 코드가 생각보다 짧더라고. 내가 Router를 구현할 때 이 로직을 그대로 따라가면 되는 건지, 그리고 논문에서 말하는 5가지 구조 타입이 코드에도 다 반영되어 있는지 확인해줘.

**Claude Code 응답 요약:**
- Router는 5가지 구조 타입(Table, Graph, Algorithm, Catalogue, Chunk) 중 하나를 선택
- `prompts/route.txt`의 few-shot 프롬프트를 LLM에 전달하고, 출력에서 단순 키워드 매칭으로 결정
- 매칭 우선순위: table > graph > algorithm > catalogue > chunk(기본값)
- 논문과 차이점 발견: 실제 프롬프트에는 table, graph, chunk 3가지만 예시로 제공

### 3.3 structurizer.py 분석

**프롬프트:**
> structurizer.py를 구현하려면 각 구조 타입별로 변환 방식이 어떻게 다른지 알아야 해. Table이랑 Graph 등 변환 로직을 분석해줘. 그리고 split_content_and_tile 함수에서 중국어 태그 같은 게 보이는데, 이건 내 구현에서 어떻게 처리해야 하는지도 알려줘.

**Claude Code 응답 요약:**
- 중국어 구분자(`<标题起始符>`, `<标题终止符>`)로 문서를 파싱 → 구현 시 제거 필요
- Table: 쿼리 키워드 기반으로 문서에서 관련 테이블 추출
- Graph: head-relation-tail 트리플로 추출
- Chunk: LLM 호출 없이 원본 그대로 사용
- 구현 시 핵심 프롬프트 로직을 유지하되, 데이터 형식은 간소화하면 됨

### 3.4 utilizer.py 분석

**프롬프트:**
> utilizer.py에 do_decompose, do_extract, do_merge 이렇게 3개 함수가 있는데, 이걸 구현하려면 각 단계의 입출력이랑 구조 타입별 추출 방식을 정확히 알아야 해. 자세히 분석해줘.

**Claude Code 응답 요약:**
- **do_decompose:** 복합 질문을 하위 질문으로 분해 (few-shot 프롬프트 사용)
- **do_extract:** 구조 타입별로 다른 추출 전략 사용
- **do_merge:** 모든 하위 질문의 추출 결과를 합쳐서 최종 답변 생성

### 3.5 qwenapi.py 분석

**프롬프트:**
> utils/qwenapi.py가 LLM API를 호출하는 부분인데, 내가 Ollama로 대체해서 구현하려면 이 인터페이스를 잘 이해해야 해. API 호출 방식이랑 에러 처리 로직을 분석해줘.

**Claude Code 응답 요약:**
- vLLM의 OpenAI-compatible API 사용 (`/v1/chat/completions`)
- OpenAI API 형식이라 Ollama도 동일한 형식 제공 → 엔드포인트만 변경하면 호환 가능
- 구현 시 OllamaAPI 클래스를 만들어 response() 메서드만 동일하게 구현하면 됨

### 3.6 프롬프트 템플릿 분석

**프롬프트:**
> prompts/ 폴더의 프롬프트 파일들을 읽어보고, 내 구현에서 어떤 프롬프트를 어떻게 활용해야 하는지 정리해줘. 논문에서는 프롬프트 내용을 자세히 안 다루니까 코드에서 직접 확인해야 할 것 같아.

**Claude Code 응답 요약:**
- **route.txt:** 3개의 few-shot 예시로 구조 타입 선택 유도 → Router 구현 시 프롬프트에 내장
- **decompose.txt:** 질문 분해 예시 4개 → Utilizer 구현 시 활용
- **construct_*.txt:** 각 구조별 변환 프롬프트 → Structurizer 구현 시 활용

---

## 4. StructRAG 파이프라인 구현 (Ollama + Qwen2.5-3B)

**프롬프트:**
> 원본 코드 분석이 끝났으니까 이제 실제로 구현해보자. 원본이 Qwen2-72B에 GPU 4장이 필요하니까, Ollama + Qwen2.5-3B로 대체해서 동일한 파이프라인을 구현해줘. Router, Structurizer, Utilizer 3개 모듈을 다 구현하고, 테스트 데이터도 만들어서 end-to-end로 돌려볼 수 있게 해줘.

**Claude Code 수행 작업:**
1. 시스템 확인: macOS 16GB RAM, Ollama 0.20.2 설치됨
2. Qwen2.5-3B 모델 다운로드 (1.9GB)
3. `run_demo.py` 구현:
   - **OllamaAPI 클래스:** 원본 QwenAPI를 Ollama OpenAI-compatible API로 재구현
   - **Router 클래스:** 원본 router.py의 few-shot 프롬프트 + 키워드 매칭 로직 구현
   - **Structurizer 클래스:** table/graph/chunk 3가지 구조 변환 구현
   - **Utilizer 클래스:** do_decompose, do_extract, do_merge 3단계 구현
   - **테스트 데이터:** 3가지 유형(통계 비교, 인용 관계, 단순 QA) 생성
   - **run_pipeline 함수:** 전체 5단계 파이프라인 실행 + 결과 저장

**구현 코드 핵심 구조:**
```python
# 1. LLM API 래퍼 (원본 QwenAPI → OllamaAPI로 대체)
class OllamaAPI:
    def response(self, input_text, max_new_tokens=2048): ...

# 2. Router (원본 router.py 재구현)
class Router:
    def do_route(self, query, core_content): ...

# 3. Structurizer (원본 structurizer.py 간소화 구현)
class Structurizer:
    def construct(self, query, chosen, docs): ...
    def construct_table(self, query, docs): ...
    def construct_graph(self, query, docs): ...
    def construct_chunk(self, docs): ...

# 4. Utilizer (원본 utilizer.py 재구현)
class Utilizer:
    def do_decompose(self, query, kb_info): ...
    def do_extract(self, query, subqueries, structured_knowledge): ...
    def do_merge(self, query, subknowledges): ...

# 5. 파이프라인 실행
def run_pipeline():
    router → structurizer → utilizer (decompose → extract → merge)
```

**실행 결과:**
| 테스트 | 기대 타입 | 실제 선택 | 소요 시간 |
|--------|-----------|-----------|-----------|
| 매출 비교 (Table) | Table | Chunk | 4.39분 |
| 인용 관계 (Graph) | Graph | Chunk | 5.21분 |
| 단순 QA (Chunk) | Chunk | Chunk | 4.33분 |

**결과 요약:**
- 3B 모델은 모든 질문에 "chunk"를 선택 → Router 정확도는 대형 모델(72B)에 크게 의존
- 인용 관계 질문(test_2)은 chunk 구조에서도 정확히 답변 → 파이프라인 자체는 정상 동작
- 일부 단계에서 CPU 추론 속도 한계로 타임아웃 발생 (원본은 10000초, 구현은 120초→600초로 수정)
- 결론: StructRAG의 핵심 가치는 Router의 정확한 구조 선택에 있고, 이를 위해선 충분히 큰 모델이 필요

---

## 5. GitHub 업로드

**프롬프트:**
> 구현이 끝났으니까 GitHub 레포(xxunivs/StructRAG)에 보고서, 프롬프트 로그, 구현 코드, 실행 결과를 전부 올려줘.

**Claude Code 수행 작업:**
- 기존 레포 클론 후 REPORT.md, PROMPTS.md, run_demo.py, demo_results.json 추가
- git commit & push 완료
