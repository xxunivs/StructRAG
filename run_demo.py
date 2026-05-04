"""
StructRAG 데모 실행 스크립트 (Ollama + Qwen2.5-3B)
원본 코드의 파이프라인을 로컬 환경에서 실행할 수 있도록 수정한 버전
"""
import json
import time
import requests
import os

# ============================================================
# 1. OllamaAPI - 원본 QwenAPI를 Ollama용으로 수정
# ============================================================
class OllamaAPI:
    """원본 utils/qwenapi.py의 QwenAPI를 Ollama OpenAI-compatible API로 대체"""
    def __init__(self, url="http://localhost:11434/v1/chat/completions", model="qwen2.5:3b"):
        self.url = url
        self.model = model

    def response(self, input_text, max_new_tokens=2048):
        current_time = time.time()

        # 입력이 너무 길면 잘라내기 (3B 모델은 컨텍스트가 작으므로)
        if len(input_text) > 8000:
            input_text = input_text[:8000]

        data = json.dumps({
            "model": self.model,
            "messages": [{"role": "user", "content": input_text}],
            "max_tokens": max_new_tokens,
            "temperature": 0.1
        })

        try:
            callback = requests.post(self.url, data=data, timeout=120)
            result = callback.json()
            response = result['choices'][0]['message']['content']
        except Exception as e:
            print(f"API Error: {e}")
            response = "Error occurred"

        elapsed = (time.time() - current_time) / 60
        print(f"  -> LLM response time: {elapsed:.2f} min")
        return response


# ============================================================
# 2. Router - 원본 router.py와 동일한 로직
# ============================================================
class Router:
    def __init__(self, llm):
        self.llm = llm

    def do_route(self, query, core_content):
        prompt = f"""Instruction:
To generate answers to questions based on documents, I need to structure the documents as a table, graph, or chunk.
Generally speaking, statistical questions prefer tables, chain reasoning questions prefer graphs, and single-hop QA questions prefer chunks.
Now, given the following document information and question, please determine which type of knowledge structure I should use.
Simply output one of the three words: table, graph, or chunk, without providing any further explanation.

Doc Info:
{core_content}

Query:
{query}

Output:"""
        output = self.llm.response(prompt)

        if "table" in output.lower():
            return "table"
        elif "graph" in output.lower():
            return "graph"
        elif "algorithm" in output.lower():
            return "algorithm"
        elif "catalogue" in output.lower():
            return "catalogue"
        else:
            return "chunk"


# ============================================================
# 3. Structurizer - 원본 structurizer.py 간소화
# ============================================================
class Structurizer:
    def __init__(self, llm):
        self.llm = llm

    def construct(self, query, chosen, docs):
        if chosen == "table":
            return self.construct_table(query, docs)
        elif chosen == "graph":
            return self.construct_graph(query, docs)
        else:  # chunk
            return self.construct_chunk(docs)

    def construct_table(self, query, docs):
        prompt = f"""Instruction:
Extract complete relevant tables from the document based on the query.
Retain table titles and source information.

Document:
{docs}

Query:
{query}

Output:"""
        output = self.llm.response(prompt)
        return "table", output

    def construct_graph(self, query, docs):
        prompt = f"""Instruction:
Extract triplets from the document. Output format: {{"head": "...", "relation": "...", "tail": ["...", "..."]}}

Document:
{docs}

Query:
{query}

Output:"""
        output = self.llm.response(prompt)
        return "graph", output

    def construct_chunk(self, docs):
        return "chunk", docs


# ============================================================
# 4. Utilizer - 원본 utilizer.py 간소화
# ============================================================
class Utilizer:
    def __init__(self, llm):
        self.llm = llm

    def do_decompose(self, query, kb_info):
        prompt = f"""Instruction:
Break down the given Query into multiple simple and independent sub-problems.
If the query is already simple enough, no breakdown is needed.

Doc Info:
{kb_info[:500]}

Query:
{query}

Output:"""
        output = self.llm.response(prompt)
        subqueries = [sq.strip() for sq in output.split("\n") if sq.strip()]
        return subqueries

    def do_extract(self, query, subqueries, structured_knowledge):
        composed_query = "\n".join(subqueries)
        prompt = f"""Instruction:
Answer the Query based on the given Document.

Query:
{composed_query}

Document:
{structured_knowledge[:3000]}

Output:"""
        output = self.llm.response(prompt)
        return output

    def do_merge(self, query, subknowledges):
        prompt = f"""Instruction:
1. Answer the Question based on retrieval results.
2. Find the relevant information and output as detailed as possible.
3. The output must be a coherent and smooth piece of text.

Question:
{query}

Retrieval:
{subknowledges}

Output:"""
        answer = self.llm.response(prompt)
        return answer


# ============================================================
# 5. 테스트 데이터 & 파이프라인 실행
# ============================================================
def create_test_data():
    """StructRAG 파이프라인을 테스트하기 위한 샘플 데이터 3개"""
    return [
        {
            "id": "test_1_table",
            "query": "Compare the revenue and profit of Company A, B, and C in 2024. Which company has the best financial performance?",
            "docs": "Company A reported revenue of $50M and profit of $8M in 2024. The company expanded to 3 new markets. Company B reported revenue of $72M and profit of $12M in 2024. They launched 5 new products. Company C reported revenue of $45M and profit of $15M in 2024. Their profit margin was the highest in the industry.",
            "expected_type": "table (statistical comparison)"
        },
        {
            "id": "test_2_graph",
            "query": "What are the citation relationships between Paper X, Paper Y, and Paper Z? Paper X cites Paper Y, and Paper Z cites both Paper X and Paper Y.",
            "docs": "Paper X: 'Attention Is All You Need' introduces the Transformer architecture. It references foundational work in sequence modeling. Paper Y: 'Neural Machine Translation by Jointly Learning to Align and Translate' proposes the attention mechanism for NMT. Paper Z: 'BERT: Pre-training of Deep Bidirectional Transformers' builds upon the Transformer (Paper X) and attention mechanism (Paper Y) for language understanding.",
            "expected_type": "graph (citation chain reasoning)"
        },
        {
            "id": "test_3_chunk",
            "query": "What is the main contribution of the StructRAG paper?",
            "docs": "StructRAG proposes a hybrid information structuring mechanism for knowledge-intensive reasoning tasks. The framework consists of three modules: a Hybrid Structure Router that selects the optimal structure type, a Scattered Knowledge Structurizer that converts documents into structured formats, and a Structured Knowledge Utilizer that decomposes questions and extracts information for answer inference.",
            "expected_type": "chunk (simple single-hop QA)"
        }
    ]


def run_pipeline():
    print("=" * 60)
    print("StructRAG Demo Pipeline (Ollama + Qwen2.5-3B)")
    print("=" * 60)

    # LLM 초기화
    llm = OllamaAPI()

    # 모듈 초기화
    router = Router(llm)
    structurizer = Structurizer(llm)
    utilizer = Utilizer(llm)

    # 테스트 데이터
    test_data = create_test_data()
    results = []

    for i, data in enumerate(test_data):
        print(f"\n{'=' * 60}")
        print(f"[Test {i+1}/{len(test_data)}] ID: {data['id']}")
        print(f"Query: {data['query'][:80]}...")
        print(f"Expected type: {data['expected_type']}")
        print("-" * 60)

        start_time = time.time()

        # Step 1: Router - 구조 타입 선택
        print("\n[Step 1] Router - Selecting structure type...")
        chosen = router.do_route(data['query'], f"Documents about: {data['docs'][:100]}")
        print(f"  -> Chosen structure: {chosen}")

        # Step 2: Structurizer - 문서 구조화
        print(f"\n[Step 2] Structurizer - Converting to {chosen} format...")
        struct_type, structured_knowledge = structurizer.construct(data['query'], chosen, data['docs'])
        print(f"  -> Structured knowledge (first 200 chars): {structured_knowledge[:200]}")

        # Step 3: Utilizer - 질문 분해
        print("\n[Step 3] Utilizer - Decomposing question...")
        subqueries = utilizer.do_decompose(data['query'], structured_knowledge)
        print(f"  -> Sub-queries: {subqueries}")

        # Step 4: Utilizer - 정보 추출
        print("\n[Step 4] Utilizer - Extracting information...")
        subknowledges = utilizer.do_extract(data['query'], subqueries, structured_knowledge)
        print(f"  -> Extracted (first 200 chars): {subknowledges[:200]}")

        # Step 5: Utilizer - 최종 답변 생성
        print("\n[Step 5] Utilizer - Generating final answer...")
        answer = utilizer.do_merge(data['query'], subknowledges)

        elapsed = (time.time() - start_time) / 60
        print(f"\n{'=' * 60}")
        print(f"FINAL ANSWER:")
        print(f"{answer}")
        print(f"\nTotal time: {elapsed:.2f} min")

        results.append({
            "id": data['id'],
            "query": data['query'],
            "chosen_type": chosen,
            "expected_type": data['expected_type'],
            "subqueries": subqueries,
            "answer": answer,
            "time_min": round(elapsed, 2)
        })

    # 결과 저장
    output_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "demo_results.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"\n\nResults saved to {output_path}")


if __name__ == "__main__":
    run_pipeline()
