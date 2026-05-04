# PROMPTS.md - AI 코딩 툴 프롬프트 로그

**사용 도구:** Claude Code (Anthropic, claude-opus-4-6 모델)

**과제:** StructRAG 논문 오픈소스 코드 분석

**작성일:** 2026-05-04

---

## 1. 과제 이해 및 계획 수립

**프롬프트:**
> 교수님이 AI 코딩 툴을 이용하여 타겟논문의 오픈소스 코드 구현 및 분석 과제를 내셨는데, 이게 무슨 말인지 설명해줘. 나는 StructRAG 논문을 할 거야. Desktop에 논문 PDF랑 발표자료, 요약자료가 있는데, 오픈소스 코드 분석이랑 프롬프트 기록을 해줘. 보고서랑 과제 어떻게 할지 계획 세워줘.

**Claude Code 응답 요약:**
- 과제 구조를 정리: 논문의 코드를 AI 코딩 툴(Claude Code)로 구현/분석하고, 그 과정의 프롬프트를 PROMPTS.md에 기록하는 것
- 4단계 계획 수립: (1) 댓글 제출 (2) 코드 구조 분석 (3) 핵심 모듈 분석 (4) 보고서 작성
- 제출물: 보고서(REPORT.md) + 프롬프트 로그(PROMPTS.md) -> GitHub 업로드 + 이메일 제출

---

## 2. 오픈소스 코드 탐색

**프롬프트:**
> StructRAG 오픈소스 코드를 찾아서 클론하고, 전체 파일 구조를 보여줘.

**Claude Code 수행 작업:**
1. 웹 검색으로 GitHub 레포 확인: https://github.com/icip-cas/StructRAG
2. 논문 PDF에서도 GitHub 링크 확인 (https://github.com/Li-Z-Q/StructRAG, 현재 icip-cas 조직으로 이전됨)
3. 레포 클론: `/Users/univ/Desktop/수업/캡디1/StructRAG`
4. 전체 파일 목록 출력

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
> main.py의 전체 코드를 읽고 실행 흐름을 분석해줘.

**Claude Code 응답 요약:**
- `main.py`는 CLI 인자로 LLM API 서버 URL, 워커 ID 등을 받음
- QwenAPI 클래스로 vLLM 서버에 연결
- Loong 벤치마크 데이터를 로드하여 200개씩 분할 처리
- 각 데이터에 대해 Router -> Structurizer -> Utilizer 순으로 파이프라인 실행
- 중간 결과와 최종 결과를 JSONL 파일로 저장
- 에러 발생 시 별도 에러 파일에 기록하고 다음 데이터로 진행

### 3.2 router.py 분석

**프롬프트:**
> router.py 코드를 분석해줘. 어떤 구조 타입들이 있고, 어떻게 선택하는지 설명해줘.

**Claude Code 응답 요약:**
- Router는 5가지 구조 타입(Table, Graph, Algorithm, Catalogue, Chunk) 중 하나를 선택
- `prompts/route.txt`의 few-shot 프롬프트를 LLM에 전달하고, 출력에서 키워드 매칭으로 결정
- 매칭 우선순위: table > graph > algorithm > catalogue > chunk(기본값)
- 실제 프롬프트에는 table, graph, chunk 3가지만 예시로 제공 (논문과 차이)

### 3.3 structurizer.py 분석

**프롬프트:**
> structurizer.py 코드를 분석해줘. 각 구조 타입별로 어떻게 문서를 변환하는지 설명해줘.

**Claude Code 응답 요약:**
- 중국어 구분자(`<标题起始符>`, `<标题终止符>`)로 문서를 제목/본문으로 파싱
- Table: 쿼리 키워드 기반으로 문서에서 관련 테이블 추출
- Graph: 논문 제목을 엔티티로, 인용 관계를 트리플로 추출 (head-relation-tail)
- Algorithm: 의사코드(pseudocode) 형태로 절차 추출
- Catalogue: 계층적 요약(hierarchical summary) 구성
- Chunk: LLM 호출 없이 원본 그대로 사용
- 각 결과는 JSON 파일로 저장하여 Utilizer에서 재사용

### 3.4 utilizer.py 분석

**프롬프트:**
> utilizer.py 코드를 분석해줘. 3단계(분해, 추출, 병합)가 어떻게 동작하는지 설명해줘.

**Claude Code 응답 요약:**
- **do_decompose:** 복합 질문을 하위 질문으로 분해 (few-shot 프롬프트 사용)
- **do_extract:** 구조 타입별로 다른 추출 전략 사용
  - Chunk: 각 청크에서 직접 답변 추출
  - Table/Graph/Algorithm/Catalogue: 전체 구조화 결과에서 하위 질문별 필터링
- **do_merge:** 모든 하위 질문의 추출 결과를 합쳐서 최종 답변 생성

### 3.5 qwenapi.py 분석

**프롬프트:**
> utils/qwenapi.py의 LLM 호출 방식을 분석해줘.

**Claude Code 응답 요약:**
- vLLM의 OpenAI-compatible API 사용 (`/v1/chat/completions`)
- GPT-2 토크나이저로 입력 길이 사전 측정, 128K 초과 시 자동 truncation
- 최대 3회 재시도, 토큰 초과 에러 시 동적으로 입력 축소
- 실행 시간 로깅 포함

### 3.6 프롬프트 템플릿 분석

**프롬프트:**
> prompts/ 폴더의 모든 프롬프트 파일(route.txt, decompose.txt, construct_*.txt)을 읽고 분석해줘.

**Claude Code 응답 요약:**
- **route.txt:** 3개의 few-shot 예시 (table/chunk/graph)로 구조 타입 선택 유도
- **decompose.txt:** 복합 질문을 하위 질문으로 분해하는 4개의 few-shot 예시
- **construct_table.txt:** 키워드 기반 테이블 추출 지시
- **construct_graph.txt:** head-relation-tail 트리플 추출, 2개의 상세 예시 포함
- **construct_algorithm.txt:** 의사코드 형태의 알고리즘 추출, 컴퓨터 조립 예시 포함
- **construct_catalogue.txt:** 계층적 요약 구성, 팟캐스트 분석 예시 포함

### 3.7 DPO 학습 코드 분석

**프롬프트:**
> train_router/dpo.py와 학습 데이터 형식을 분석해줘.

**Claude Code 응답 요약:**
- HuggingFace TRL의 DPOTrainer 사용
- (chosen, rejected) 선호도 쌍으로 구성된 학습 데이터
- DeepSpeed ZeRO, FSDP 등 분산 학습 지원
- Qwen 모델의 bos_token 미설정 이슈를 코드에서 직접 처리

---

## 4. 보고서 작성

**프롬프트:**
> 분석 결과를 바탕으로 REPORT.md 보고서를 작성해줘. 논문 개요, 코드 구조, 핵심 모듈 분석, 실행 매뉴얼, 인사이트를 포함해줘.

**Claude Code 응답 요약:**
- 5개 섹션으로 구성된 보고서 작성 완료
- 논문 vs 코드 차이점, 설계 특징, 한계점 등 인사이트 포함

---

## 5. GitHub 업로드

**프롬프트:**
> 기존 GitHub 레포(xxunivs/StructRAG)에 REPORT.md와 PROMPTS.md를 올려줘.

**Claude Code 수행 작업:**
- 기존 레포 클론 후 파일 추가
- git commit & push
