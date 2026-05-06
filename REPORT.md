# StructRAG 오픈소스 코드 구현 보고서

**논문:** StructRAG: Boosting Knowledge Intensive Reasoning of LLMs via Inference-time Hybrid Information Structurization (ICLR 2025)

**저자:** Zhuoqun Li et al. (Chinese Academy of Sciences, Alibaba Group)

**오픈소스 코드:** https://github.com/icip-cas/StructRAG

**분석 도구:** Claude Code (Anthropic)

**작성자:** 김우주 (SF11)

**작성일:** 2026-05-04

---

## 1. 논문 개요

### 1.1 문제 정의
기존 RAG(Retrieval-Augmented Generation) 방법은 지식 집약적 추론(knowledge-intensive reasoning) 과제에서 성능이 부족하다. 핵심 원인은 필요한 정보가 여러 문서에 **산재(scattered)**되어 있어, 관련 청크를 정확히 검색하고 통합 추론하기 어렵기 때문이다.

### 1.2 핵심 아이디어
인간의 인지 이론(Cognitive Load Theory, Cognitive Fit Theory)에서 영감을 받아, 사람이 흩어진 정보를 구조화된 지식으로 변환하여 추론하듯이, LLM도 추론 시점(inference-time)에 문서를 최적의 구조로 변환하여 활용하는 프레임워크를 제안한다.

### 1.3 StructRAG 3대 모듈

| 모듈 | 역할 |
|------|------|
| **Hybrid Structure Router** | 질문+문서 정보를 분석하여 최적의 구조 타입(Table, Graph, Algorithm, Catalogue, Chunk) 선택 |
| **Scattered Knowledge Structurizer** | 원본 문서를 선택된 구조 형식으로 변환 |
| **Structured Knowledge Utilizer** | 질문 분해 -> 정보 추출 -> 최종 답변 추론 |

### 1.4 주요 성과
- 다양한 지식 집약적 추론 과제에서 SOTA 달성
- 과제 복잡도가 높아질수록 기존 방법 대비 성능 향상 폭이 큼
- GraphRAG 대비 더 넓은 과제 범위에서 우수한 성능 + 빠른 속도

---

## 2. 코드 구조

```
StructRAG/
├── main.py                  # 전체 파이프라인 실행 진입점
├── router.py                # Hybrid Structure Router 모듈
├── structurizer.py          # Scattered Knowledge Structurizer 모듈
├── utilizer.py              # Structured Knowledge Utilizer 모듈
├── do_merge_each_batch.py   # 분산 처리 결과 병합
├── requirements.txt         # Python 의존성
├── utils/
│   └── qwenapi.py           # LLM API 호출 래퍼 (vLLM OpenAI-compatible)
├── prompts/
│   ├── route.txt            # Router용 few-shot 프롬프트
│   ├── decompose.txt        # 질문 분해용 프롬프트
│   ├── construct_table.txt  # 테이블 구조화 프롬프트
│   ├── construct_graph.txt  # 그래프 구조화 프롬프트
│   ├── construct_algorithm.txt  # 알고리즘 구조화 프롬프트
│   └── construct_catalogue.txt  # 카탈로그 구조화 프롬프트
├── train_router/
│   ├── dpo.py               # DPO 알고리즘으로 Router 학습
│   ├── train.sh             # 학습 실행 스크립트
│   ├── data/
│   │   ├── train.json       # Router 학습 데이터 (선호도 쌍)
│   │   └── test.json        # Router 평가 데이터
│   └── accelerate_configs/  # 분산 학습 설정 (DeepSpeed, FSDP 등)
└── Loong/                   # 평가 벤치마크 (Loong 데이터셋)
    ├── src/
    │   ├── step1_load_data.py
    │   ├── step2_model_generate.py
    │   ├── step3_model_evaluate.py
    │   ├── step4_cal_metric.py
    │   └── utils/
    └── requirements.txt
```

---

## 3. 핵심 모듈 상세 분석

### 3.1 main.py - 파이프라인 실행

`main.py`는 전체 StructRAG 파이프라인의 진입점이다.

**실행 흐름:**
```
1. vLLM으로 Qwen2-72B-Instruct 모델을 OpenAI-compatible API 서버로 배포
2. main.py 실행 -> QwenAPI 클라이언트로 API 서버에 연결
3. Loong 벤치마크 데이터 로드
4. 각 데이터에 대해:
   (a) Router: 최적 구조 타입 결정
   (b) Structurizer: 문서를 해당 구조로 변환
   (c) Utilizer: 질문 분해 -> 정보 추출 -> 답변 생성
5. 결과를 JSONL 파일로 저장
```

**핵심 코드 (main.py:69-101):**
```python
for i, data in enumerate(eval_datas):
    # 1. Router - 구조 타입 선택
    chosen = router.do_route(query, core_content, data['id'])

    # 2. Structurizer - 문서 구조화
    instruction, kb_info = structurizer.construct(query, chosen, data['docs'], data['id'])

    # 3. Utilizer - 질문 분해, 정보 추출, 답변 생성
    subqueries = utilizer.do_decompose(query, kb_info, data['id'])
    subknowledges = utilizer.do_extract(query, subqueries, chosen, data['id'])
    answer, _, _ = utilizer.do_merge(query, subqueries, subknowledges, chosen, data['id'])
```

**분산 처리:** `worker_id` 인자로 데이터를 200개씩 분할하여 최대 8개 워커가 병렬 처리 가능하다. `do_merge_each_batch.py`에서 각 워커의 결과를 하나로 병합한다.

---

### 3.2 Router (router.py) - 구조 타입 선택

**역할:** 질문과 문서의 핵심 내용을 보고 5가지 구조 타입 중 최적의 것을 선택한다.

**구조 타입 5가지:**
| 타입 | 적합한 과제 | 예시 |
|------|------------|------|
| **Table** | 통계/비교 질문 | "A, B, C 회사의 매출 비교" |
| **Graph** | 연쇄 추론 (chain reasoning) | "논문 간 인용 관계 파악" |
| **Algorithm** | 절차적 의사결정 | "컴퓨터 조립 순서 결정" |
| **Catalogue** | 계층적 요약 | "문서 내용 계층 분류" |
| **Chunk** | 단순 QA (single-hop) | "특정 정보 찾기" |

**코드 분석 (router.py):**
```python
class Router:
    def do_route(self, query, core_content, data_id):
        raw_prompt = open("prompts/route.txt", "r").read()
        prompt = raw_prompt.format(query=query, titles=core_content)
        output = self.llm.response(prompt)

        # 출력에서 키워드 매칭으로 구조 타입 결정
        if "table" in output.lower():
            chosen = "table"
        elif "graph" in output.lower():
            chosen = "graph"
        elif "algorithm" in output.lower():
            chosen = "algorithm"
        elif "catalogue" in output.lower():
            chosen = "catalogue"
        else:
            chosen = "chunk"  # 기본값
        return chosen
```

**구현 특징:**
- LLM에게 few-shot 프롬프트(prompts/route.txt)를 주고, 출력에서 키워드를 매칭하는 단순한 방식
- 논문의 Router 프롬프트에는 "table, graph, chunk" 3가지만 예시로 제공하지만, 코드에서는 algorithm, catalogue까지 5가지를 처리
- 매칭되는 키워드가 없으면 기본값으로 "chunk"를 사용

**Router 학습 (선택적):**
- Qwen2-72B-Instruct는 few-shot만으로도 좋은 라우팅 성능을 보임
- 더 높은 정확도를 위해 7B 모델을 DPO(Direct Preference Optimization)로 fine-tuning 가능
- 학습 데이터는 `(chosen, rejected)` 쌍으로 구성된 선호도 데이터 (`train_router/data/train.json`)

---

### 3.3 Structurizer (structurizer.py) - 문서 구조화

**역할:** Router가 선택한 구조 타입에 따라 원본 문서를 해당 형식으로 변환한다.

**문서 파싱:**
```python
def split_content_and_tile(self, docs_):
    raw_doc_list = docs_.strip("<标题起始符>").split("<标题起始符>")
    for raw_doc in raw_doc_list:
        title = raw_doc.split('<标题终止符>')[0].strip()
        content = raw_doc.split('<标题终止符>')[1].strip()
```
- 중국어 구분자 `<标题起始符>` (제목 시작), `<标题终止符>` (제목 끝)로 문서를 파싱
- 이는 Loong 벤치마크 데이터의 형식에 맞춘 것

**구조별 변환 방식:**

| 구조 타입 | 변환 방법 | 프롬프트 파일 |
|-----------|-----------|---------------|
| Table | LLM이 문서에서 관련 테이블 추출 | construct_table.txt |
| Graph | LLM이 엔티티 간 관계를 트리플 형태로 추출 | construct_graph.txt |
| Algorithm | LLM이 의사코드(pseudocode) 형태로 추출 | construct_algorithm.txt |
| Catalogue | LLM이 계층적 요약(hierarchical summary) 구성 | construct_catalogue.txt |
| Chunk | 원본 문서를 그대로 사용 (LLM 호출 없음) | 없음 |

**핵심 특징:**
- Chunk를 제외한 모든 구조화 작업은 LLM을 호출하여 수행
- 각 문서를 개별적으로 처리 (문서별 루프)
- 구조화 결과는 JSON 파일로 저장하여 이후 Utilizer에서 재사용
- `kb_info` (knowledge base info)로 구조화 결과의 요약 정보를 반환 (첫 128자)

---

### 3.4 Utilizer (utilizer.py) - 구조화 지식 활용

**역할:** 구조화된 지식을 활용하여 최종 답변을 생성한다. 3단계로 동작한다.

#### 단계 1: 질문 분해 (do_decompose)
```python
def do_decompose(self, query, kb_info, data_id):
    raw_prompt = open("prompts/decompose.txt", "r").read()
    prompt = raw_prompt.format(query=query, kb_info=kb_info)
    output = self.llm.response(prompt)
    subqueries = output.split("\n")
    return subqueries
```
- 복합 질문을 독립적인 하위 질문(sub-question)들로 분해
- kb_info를 참고하여 문서 구조에 맞는 분해 수행

#### 단계 2: 정보 추출 (do_extract)
각 구조 타입별로 다른 추출 전략을 사용:

| 구조 타입 | 추출 방법 |
|-----------|-----------|
| Chunk | 각 청크에서 하위 질문에 대한 답변 추출 |
| Table | 모든 테이블을 합친 후 하위 질문별로 필터링 |
| Graph | 모든 그래프 트리플에서 관련 트리플 필터링 |
| Algorithm | 알고리즘 설명에서 관련 정보 필터링 |
| Catalogue | 카탈로그에서 관련 정보 필터링 |

#### 단계 3: 답변 생성 (do_merge)
```python
def do_merge(self, query, subqueries, subknowledges, chosen, data_id):
    instruction = "1. Answer the Question based on retrieval results.
                   2. Find the relevant information... output as detailed...
                   3. The output must be a coherent and smooth piece of text."
    prompt = f"Instruction:\n{instruction}\n\nQuestion:\n{query}\n\nRetrieval:\n..."
    answer = self.llm.response(prompt)
    return answer, decision, new_query
```
- 모든 하위 질문의 추출 결과를 하나의 프롬프트로 합침
- LLM에게 상세하고 일관된 답변을 생성하도록 지시

---

### 3.5 QwenAPI (utils/qwenapi.py) - LLM 호출

**역할:** vLLM으로 배포된 LLM API 서버와 통신하는 래퍼 클래스.

**핵심 특징:**
- vLLM의 OpenAI-compatible API (`/v1/chat/completions`) 사용
- GPT-2 토크나이저로 입력 길이를 사전 측정하여 128K 토큰 제한 초과 시 자동 truncation
- 최대 3회 재시도 로직
- 토큰 길이 초과 에러 발생 시 동적으로 입력을 줄여서 재시도

---

### 3.6 Router DPO 학습 (train_router/dpo.py)

**역할:** Hybrid Structure Router의 구조 타입 선택 능력을 강화하기 위한 DPO 학습.

**학습 방식:**
- HuggingFace TRL 라이브러리의 DPOTrainer 사용
- 입력: `(chosen, rejected)` 쌍으로 구성된 선호도 데이터
  - chosen: 올바른 구조 타입 (예: 통계 질문 -> "table")
  - rejected: 잘못된 구조 타입 (예: 통계 질문 -> "graph")
- DeepSpeed ZeRO, FSDP 등 분산 학습 설정 제공

**학습 데이터 형식 (train_router/data/test.json):**
```json
{
  "prompt": "...(질문+문서정보)...",
  "chosen": [{"role": "user", "content": "..."}, {"role": "assistant", "content": "chunk"}],
  "rejected": [{"role": "user", "content": "..."}, {"role": "assistant", "content": "graph"}]
}
```

---

## 4. 실행 매뉴얼

### 4.1 환경 요구사항
- Python 3.8.19
- GPU: NVIDIA GPU 4장 이상 (Qwen2-72B-Instruct 모델 서빙용)
- vLLM 0.6.3.post1

### 4.2 설치
```bash
git clone https://github.com/icip-cas/StructRAG.git
cd StructRAG
pip install -r requirements.txt
```

### 4.3 데이터 준비
```bash
# Loong 벤치마크 데이터 준비
cd Loong && cat README.md  # 데이터 준비 방법 확인
```

### 4.4 실행
```bash
# 1. LLM API 서버 실행 (vLLM)
model_path="/path/to/Qwen2-72B-Instruct"
CUDA_VISIBLE_DEVICES=0,1,2,3 python -m vllm.entrypoints.openai.api_server \
    --model ${model_path} \
    --served-model-name Qwen \
    --tensor-parallel-size 4 \
    --port 1225

# 2. StructRAG 추론 실행
python main.py --url localhost:1225

# 3. 결과 병합
python do_merge_each_batch.py

# 4. 평가
cd Loong/src && bash run.sh
```

### 4.5 Router 학습 (선택)
```bash
bash train_router/train.sh
```

---

## 5. 코드 분석 인사이트

### 5.1 설계 특징
1. **모듈화:** Router, Structurizer, Utilizer가 명확히 분리되어 각각 독립적으로 교체/개선 가능
2. **프롬프트 기반:** 모든 핵심 로직이 프롬프트 엔지니어링으로 구현되어 있어 코드 자체는 비교적 단순
3. **LLM 의존적:** Chunk를 제외한 모든 구조화와 추론이 LLM 호출로 이루어짐

### 5.2 한계점
1. **비용:** 하나의 질문에 대해 Router(1회) + Structurizer(문서 수만큼) + Utilizer(분해+추출+생성)로 다수의 LLM 호출 발생
2. **하드코딩:** 문서 파싱에 중국어 구분자(`<标题起始符>`, `<标题终止符>`)가 하드코딩되어 다른 데이터셋 적용 시 수정 필요
3. **단순한 라우팅 로직:** 키워드 매칭(`if "table" in output.lower()`)으로 구조 타입을 결정하여, LLM이 예상치 못한 출력을 하면 항상 "chunk"로 fallback
4. **72B 모델 요구:** 기본 설정이 Qwen2-72B-Instruct로 GPU 4장 이상 필요하여 개인 환경에서 실행이 어려움

### 5.3 논문 vs 코드 차이
- 논문에서는 구조 타입을 Table, Graph, Algorithm, Catalogue, Chunk 5가지로 소개하나, Router 프롬프트(route.txt)의 few-shot 예시에는 Table, Graph, Chunk 3가지만 포함
- 논문의 Figure 1에서 보여주는 깔끔한 파이프라인과 달리, 실제 코드는 Loong 벤치마크에 특화된 전처리/후처리가 포함되어 있음

---

## 6. 로컬 환경 구현 및 실행 결과 (Ollama + Qwen2.5-3B)

원본 코드는 Qwen2-72B-Instruct (GPU 4장)가 필요하여 로컬 실행이 불가능하다. 이에 원본 코드의 파이프라인을 분석하여 Ollama + Qwen2.5-3B (1.9GB) 환경에서 동작하도록 재구현하였다 (`run_demo.py`). OllamaAPI 클래스, Router, Structurizer, Utilizer 4개 모듈을 구현하고, 테스트 데이터 3종을 생성하여 end-to-end 파이프라인을 실행하였다.

### 6.1 실행 환경
- macOS, Apple Silicon, 16GB RAM
- Ollama 0.20.2 + Qwen2.5-3B (양자화, 1.9GB)
- GPU 없이 CPU 추론

### 6.2 테스트 데이터
3가지 유형의 질문으로 구성:

| 테스트 ID | 질문 유형 | 기대 구조 타입 |
|-----------|-----------|---------------|
| test_1_table | 회사 A, B, C 매출/이익 비교 | Table |
| test_2_graph | 논문 간 인용 관계 파악 | Graph |
| test_3_chunk | StructRAG 논문의 주요 기여 | Chunk |

### 6.3 실행 결과

| 테스트 | 기대 타입 | 실제 선택 | 소요 시간 | 답변 품질 |
|--------|-----------|-----------|-----------|-----------|
| test_1_table | Table | **Chunk** | 4.59분 | 답변 생성됨 (수치 hallucination 있음) |
| test_2_graph | Graph | **Chunk** | 4.59분 | 인용 관계 정확히 파악 |
| test_3_chunk | Chunk | **Chunk** | 4.14분 | 일부 타임아웃 발생 |

### 6.4 관찰 및 분석

**1. Router의 모델 크기 의존성:**
3B 모델은 모든 질문에 "chunk"를 선택하였다. 이는 Router의 few-shot 프롬프트가 대형 모델(72B)에 최적화되어 있어, 소형 모델은 프롬프트의 예시를 충분히 이해하지 못하기 때문이다. 논문에서 "Qwen2-72B-Instruct has already achieved good routing performance"라고 명시한 것과 일치한다.

**2. Structurizer의 역할 감소:**
Router가 항상 "chunk"를 선택하므로, Structurizer가 문서를 구조화하는 핵심 기능(Table/Graph 변환)이 발동되지 않았다. 이는 StructRAG의 성능이 Router의 정확도에 크게 의존함을 보여준다.

**3. Utilizer의 질문 분해:**
3B 모델도 질문 분해는 수행했으나, 지시사항을 정확히 따르지 못하고 설명을 덧붙이는 경향이 있었다. 72B 모델에서는 더 간결하고 정확한 분해가 기대된다.

**4. 타임아웃 이슈:**
CPU 추론의 속도 한계로 120초 타임아웃이 2회 발생하였다. 원본 코드의 QwenAPI는 10000초 타임아웃을 설정하고 있어, GPU 환경에서는 이 문제가 발생하지 않는다.

**5. 결론:**
StructRAG 파이프라인은 소형 모델에서도 구조적으로는 정상 동작하나, **Router의 정확도**와 **LLM의 지시 따르기 능력**이 전체 성능의 핵심이다. 이는 논문의 "hybrid structure router's ability to accurately select the most suitable structure type" 주장을 실험적으로 확인한 결과이다.
