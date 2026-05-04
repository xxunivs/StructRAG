# PROMPTS.md - AI 코딩 툴 프롬프트 로그

**사용 도구:** Claude Code (Anthropic, claude-opus-4-6 모델)

**과제:** StructRAG 논문 오픈소스 코드 분석

**작성일:** 2026-05-04

---

## 1. 과제 파악 및 계획 수립

**프롬프트:**
> StructRAG 논문으로 오픈소스 코드 분석 과제를 하려고 하는데, 논문 PDF는 Desktop/수업/캡디1/논문에 있고, 이전에 만들어둔 발표자료랑 요약자료도 같은 폴더에 있어. 근데 발표자료랑 요약자료에서는 오픈소스 코드 분석은 안 다뤘거든. 그래서 이번에 오픈소스 코드 위주로 분석을 하고 싶은데, 어떤 순서로 진행하면 좋을지 계획을 잡아줄 수 있어?

**Claude Code 응답 요약:**
- 과제 구조를 정리: 논문의 코드를 AI 코딩 툴(Claude Code)로 분석하고, 그 과정의 프롬프트를 PROMPTS.md에 기록하는 것
- 4단계 계획 수립: (1) 댓글 제출 (2) 코드 구조 분석 (3) 핵심 모듈 분석 (4) 보고서 작성
- 제출물: 보고서(REPORT.md) + 프롬프트 로그(PROMPTS.md) -> GitHub 업로드 + 이메일 제출

---

## 2. 오픈소스 코드 탐색

**프롬프트:**
> 논문 PDF를 보니까 Abstract 아래에 GitHub 링크가 있더라고. 이 코드를 클론해서 전체 구조를 먼저 파악하고 싶어. 어떤 파일들이 있는지, 각 파일이 뭘 하는 건지 한눈에 볼 수 있게 정리해줘.

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

## 3. 핵심 모듈 코드 분석

### 3.1 main.py 분석

**프롬프트:**
> main.py가 전체 파이프라인의 진입점인 것 같은데, 코드를 읽어보니 Router, Structurizer, Utilizer를 순서대로 호출하는 구조더라고. 근데 worker_id라든지 start_bias 같은 인자들이 좀 헷갈리는데, 전체 실행 흐름이랑 이 인자들이 뭘 위한 건지 분석해줄 수 있어?

**Claude Code 응답 요약:**
- `main.py`는 CLI 인자로 LLM API 서버 URL, 워커 ID 등을 받음
- QwenAPI 클래스로 vLLM 서버에 연결
- Loong 벤치마크 데이터를 로드하여 200개씩 분할 처리 (worker_id로 병렬화)
- start_bias는 이전 실행에서 에러난 데이터를 건너뛰기 위한 오프셋
- 각 데이터에 대해 Router -> Structurizer -> Utilizer 순으로 파이프라인 실행
- 중간 결과와 최종 결과를 JSONL 파일로 저장

### 3.2 router.py 분석

**프롬프트:**
> 논문에서 Hybrid Structure Router가 핵심이라고 하는데, router.py를 보면 코드가 생각보다 짧더라고. 실제로 구조 타입을 어떻게 선택하는 건지, 그리고 논문에서 말하는 5가지 구조 타입이 코드에도 다 반영되어 있는지 확인해줘.

**Claude Code 응답 요약:**
- Router는 5가지 구조 타입(Table, Graph, Algorithm, Catalogue, Chunk) 중 하나를 선택
- `prompts/route.txt`의 few-shot 프롬프트를 LLM에 전달하고, 출력에서 단순 키워드 매칭으로 결정
- 매칭 우선순위: table > graph > algorithm > catalogue > chunk(기본값)
- 논문과 차이점 발견: 실제 프롬프트에는 table, graph, chunk 3가지만 예시로 제공되어 있고 algorithm, catalogue는 예시 없음

### 3.3 structurizer.py 분석

**프롬프트:**
> structurizer.py가 문서를 구조화하는 모듈인 건 알겠는데, Table이랑 Graph 등 각 구조 타입별로 변환 방식이 어떻게 다른지 궁금해. 그리고 split_content_and_tile 함수에서 중국어 태그 같은 게 보이는데, 이건 뭘 하는 건지도 설명해줘.

**Claude Code 응답 요약:**
- 중국어 구분자(`<标题起始符>`, `<标题终止符>`)로 문서를 제목/본문으로 파싱 (Loong 벤치마크 전용 형식)
- Table: 쿼리 키워드 기반으로 문서에서 관련 테이블 추출
- Graph: 논문 제목을 엔티티로, 인용 관계를 트리플로 추출 (head-relation-tail)
- Algorithm: 의사코드(pseudocode) 형태로 절차 추출
- Catalogue: 계층적 요약(hierarchical summary) 구성
- Chunk: LLM 호출 없이 원본 그대로 사용
- 각 결과는 JSON 파일로 저장하여 이후 Utilizer에서 재사용

### 3.4 utilizer.py 분석

**프롬프트:**
> utilizer.py에 do_decompose, do_extract, do_merge 이렇게 3개 함수가 있는데, 논문에서 말하는 "질문 분해 -> 정보 추출 -> 답변 생성" 흐름이 실제 코드에서는 어떻게 구현되어 있는지 궁금해. 특히 구조 타입별로 추출 방식이 다른 것 같은데, 이 부분을 자세히 분석해줘.

**Claude Code 응답 요약:**
- **do_decompose:** 복합 질문을 하위 질문으로 분해 (few-shot 프롬프트 사용)
- **do_extract:** 구조 타입별로 다른 추출 전략 사용
  - Chunk: 각 청크에서 직접 답변 추출
  - Table/Graph/Algorithm/Catalogue: 전체 구조화 결과에서 하위 질문별 필터링
- **do_merge:** 모든 하위 질문의 추출 결과를 합쳐서 최종 답변 생성

### 3.5 qwenapi.py 분석

**프롬프트:**
> LLM 호출하는 부분이 utils/qwenapi.py에 있는 것 같은데, vLLM이랑 어떻게 연결되는 건지, 그리고 토큰 길이 제한이나 에러 처리는 어떻게 하고 있는지 알려줘. 나중에 다른 모델로 바꿔서 돌리려면 이 부분을 이해해야 할 것 같아서.

**Claude Code 응답 요약:**
- vLLM의 OpenAI-compatible API 사용 (`/v1/chat/completions`)
- GPT-2 토크나이저로 입력 길이 사전 측정, 128K 초과 시 자동 truncation
- 최대 3회 재시도, 토큰 초과 에러 시 동적으로 입력 축소
- OpenAI API 형식이라 Ollama 등 다른 서버로 교체 가능

### 3.6 프롬프트 템플릿 분석

**프롬프트:**
> prompts/ 폴더에 route.txt, decompose.txt, construct_table.txt 같은 파일들이 있는데, 이 프롬프트들이 실제로 LLM에 어떤 지시를 내리는 건지 전부 읽어보고 정리해줘. 논문에서는 프롬프트 내용을 자세히 안 다루니까, 코드에서 직접 확인해야 할 것 같아.

**Claude Code 응답 요약:**
- **route.txt:** 3개의 few-shot 예시 (table/chunk/graph)로 구조 타입 선택 유도
- **decompose.txt:** 복합 질문을 하위 질문으로 분해하는 4개의 few-shot 예시
- **construct_table.txt:** 키워드 기반 테이블 추출 지시
- **construct_graph.txt:** head-relation-tail 트리플 추출, 2개의 상세 예시 포함
- **construct_algorithm.txt:** 의사코드 형태의 알고리즘 추출, 컴퓨터 조립 예시 포함
- **construct_catalogue.txt:** 계층적 요약 구성, 팟캐스트 분석 예시 포함

### 3.7 DPO 학습 코드 분석

**프롬프트:**
> train_router/ 폴더에 Router를 DPO로 학습하는 코드가 있는 것 같은데, 학습 데이터가 어떤 형식이고 어떻게 학습시키는 건지 분석해줘. 논문에서 "preference training data"로 Router를 학습한다고 했는데, 실제 데이터를 보면 이해가 더 잘 될 것 같아서.

**Claude Code 응답 요약:**
- HuggingFace TRL의 DPOTrainer 사용
- (chosen, rejected) 선호도 쌍으로 구성된 학습 데이터
  - 예: 통계 질문 -> chosen: "table", rejected: "graph"
- DeepSpeed ZeRO, FSDP 등 분산 학습 지원
- Qwen 모델의 bos_token 미설정 이슈를 코드에서 직접 처리

---

## 4. 로컬 실행 (Ollama + Qwen2.5-3B)

**프롬프트:**
> 코드 분석만 하니까 뭔가 부족한 것 같아서, 실제로 돌려보고 싶거든. 근데 원본 코드가 Qwen2-72B에 GPU 4장이 필요하다고 했잖아. 내 맥북에서 돌릴 수 있는 대안이 있을까? Ollama가 설치되어 있는데, 작은 모델로 대체해서 파이프라인이 동작하는지 정도만이라도 확인하고 싶어.

**Claude Code 수행 작업:**
1. 시스템 확인: macOS 16GB RAM, Ollama 0.20.2 설치됨
2. Qwen2.5-3B 모델 다운로드 (1.9GB)
3. 원본 코드의 파이프라인(Router -> Structurizer -> Utilizer)을 Ollama API로 수정한 데모 스크립트(`run_demo.py`) 작성
4. 3가지 유형의 테스트 데이터(통계 비교, 인용 관계, 단순 QA) 생성하여 실행

**실행 결과:**
| 테스트 | 기대 타입 | 실제 선택 | 소요 시간 |
|--------|-----------|-----------|-----------|
| 매출 비교 (Table) | Table | Chunk | 4.59분 |
| 인용 관계 (Graph) | Graph | Chunk | 4.59분 |
| 단순 QA (Chunk) | Chunk | Chunk | 4.14분 |

**응답 요약:**
- 3B 모델은 모든 질문에 "chunk"를 선택 -> Router 정확도는 대형 모델(72B)에 크게 의존
- 인용 관계 질문(test_2)은 chunk 구조에서도 정확히 답변했지만, graph로 구조화했다면 더 정교했을 것
- 일부 단계에서 CPU 추론 속도 한계로 타임아웃 발생 (원본은 10000초 타임아웃, 데모는 120초)
- 결론: StructRAG의 핵심 가치는 Router의 정확한 구조 선택에 있고, 이를 위해선 충분히 큰 모델이 필요

---

## 5. GitHub 업로드

**프롬프트:**
> 분석이 끝났으니까 기존에 만들어둔 GitHub 레포(xxunivs/StructRAG)에 보고서랑 프롬프트 로그, 데모 스크립트까지 전부 올려줘.

**Claude Code 수행 작업:**
- 기존 레포 클론 후 REPORT.md, PROMPTS.md, run_demo.py, demo_results.json 추가
- git commit & push 완료
