import os
import json
import re
import requests
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from rag_context import build_rag_prompt_section

PROVIDER_GEMINI = "gemini"
PROVIDER_OPENAI = "openai"
PROVIDER_ANTHROPIC = "anthropic"

MODEL_MAP = {
    PROVIDER_GEMINI: "gemini-2.5-flash",
    PROVIDER_OPENAI: "gpt-4o-mini",
    PROVIDER_ANTHROPIC: "claude-haiku-4-5-20251001"
}

SYSTEM_PROMPT = """당신은 대한민국 최고의 맞춤법, 띄어쓰기 및 공문서 작성 전문가입니다.
오직 다음 항목만 찾아주시고, 반드시 순수 JSON(errors 배열)만 출력하세요.

[오타 검출 규칙]
1. 단순 맞춤법/철자 오류 (예: '됬다' → '됐다', '않습니다' → '안 합니다')
2. 띄어쓰기 오류 (예: '국민은행입구' → '국민은행 입구')
3. 개조식/표 안에서 문맥상 명백한 오타 (예: '예산잔액' vs '예산 잔액')

[출력 데이터 작성 주의사항]
- 사용자가 오타를 쉽게 검색할 수 있도록, 짧은 숫자나 단어 하나('03.' 등)만 적지 말고 문맥이 드러나는 어절 단위나 연월일 전체('2024. 03.' 등)를 original과 corrected에 포함하세요.

[반드시 제외할 항목]
- 연도 표기 시 ' ('24년, '25년 등) 표현은 정상적인 줄임표 표현이므로 수정하지 마세요.
- 개조식 문단(□, ○, -, · 등)은 현재 상태 그대로 놔두세요. 마침표(.)가 없는 것도 정상입니다.
- 개조식 문장 끝에 마침표(.)가 누락된 것은 오타나 문법 오류로 간주하지 마세요.
- 문장 끝이 '바람', '함', '임', '음' 등으로 끝나는 개조식 종결 어미를 '바랍니다', '합니다' 등 서술식으로 바꾸는 제안은 절대 하지 마세요. (예: '실시하기 바람' → '실시해 주시기 바랍니다' 제안 금지)
- 문체나 어감 변경을 위한 제안(예: "권위적인 표현을 정중한 표현으로 변경")은 절대 하지 마세요. 오직 명백한 맞춤법/띄어쓰기 오류만 지적하세요.
- 문장 완성 제안 금지: 구문이 끊기거나 미완성된 채로 끝나더라도, 뒤에 내용을 덧붙이거나 서술형으로 완성하라는 제안은 절대 하지 마세요.
- HTML 엔티티(&#숫자;, &lt; 등)는 깨진 문자열로 간주하지 않고 무시하세요.
- 고유명사/기관명/법령명은 수정하지 마세요.
- 숫자/금액/날짜 표기 방식 차이는 정상 표현입니다.
- **가운뎃점(·, ㆍ, ‧, ・ 등) 절대 허용**: 어떤 형태의 가운뎃점이든, 앞뒤에 띄어쓰기가 있든 없든(예: 'A·B', 'A · B', 'A  ·  B' 등) 절대 오타나 띄어쓰기 오류로 지적하지 마세요. 이는 사용자의 고유한 스타일입니다.
- **특수문자 활용 허용**: 문장 내에서 별표(*, ※) 등을 사용하여 주석을 표기하거나 강조하는 것은 정상적인 표현이므로 오타로 인식하지 마세요. (예: '보고서* 작성' 등)
- **'-적' 관형사적 용법 허용**: 명사 뒤에 '-적'이 붙어 뒤의 명사를 수식하는 표현(예: '안정적 주거', '자율적 구조개선' 등)은 문법적으로 허용되므로 '안정적인' 등으로 수정하라고 지적하지 마세요.
- **업무 전문 용어 허용**: '예결산'(예산과 결산의 줄임말), '대상교'(대상 학교의 줄임말) 등 실무에서 관행적으로 붙여 쓰는 단어나 전문 용어는 오타로 지적하지 마세요.
- **닫는 부호 뒤 접미사 보존**: 앞말이 닫는 부호(」, ), ], } 등)로 끝나고 그 뒤에 접미사(-상, -간, -적 등)가 올 경우, 절대 부호를 삭제하지 마세요. 부호를 유지한 채 그 뒤에 접미사를 붙여 쓰도록 제안하세요. (예: '법률」 상' → '법률」상' (O), '법률상' (X - 부호 삭제 금지))
- 표 텍스트는 셀 간 경계가 불분명하므로 단어가 붙어 있어도 그대로 두세요.
- **표준어 보존 및 오탐 방지**: '횟수', '개수', '건수', '점수' 등은 그 자체로 하나의 명사입니다. '회 수'와 같이 띄어 쓰라는 지적은 명백한 오탐이므로 절대 하지 마세요.
- 의존 명사(수, 것, 데 등)로 의심되더라도, 단어가 사전에 한 단어(명사)로 등록되어 있다면 띄어쓰기 수정을 제안하지 마세요.
- meta에 "글자단위띄어쓰기(의도적서식)"가 포함된 문장은 가독성을 위한 의도적 서식이므로 어떤 오류도 지적하지 마세요.
- **외래어 표기법 지적 금지**: 외래어 표기법에 따른 수정 제안(예: '컨텐츠' → '콘텐츠', '디지탈' → '디지털', '스케쥴' → '스케줄' 등)은 절대 하지 마세요. 사용자가 작성한 외래어 표기를 그대로 존중하세요.

[출력 JSON 스키마 - 반드시 이 필드명을 사용하세요]
{
  "errors": [
    {
      "page": 1,
      "sentence": "오류가 포함된 전체 문장",
      "original": "수정 전 오류 표현 (검색이 용이하도록 주변 단어 포함)",
      "corrected": "수정 후 올바른 표현",
      "reason": "오류 이유 설명",
      "errorType": "spelling | spacing | grammar"
    }
  ]
}
오류가 없으면 {"errors": []} 을 반환하세요.
"""

def build_user_prompt(doc):
    sentences = doc.get("sentences", [])
    lines = []
    for idx, sentence in enumerate(sentences):
        text = re.sub(r"\s+", " ", (sentence.get("text") or "")).replace('"', '\\"')
        meta = (sentence.get("meta") or "meta 없음").replace("|", "\\|")
        lines.append(f'{idx + 1}. text="{text}" | meta="{meta}" | page={sentence.get("pageNumber", "?")}')
    
    list_section = "\n".join(lines) if lines else "검사할 문장이 없습니다."
    title = (doc.get("metadata") or {}).get("title") or os.path.basename(doc.get("file", "문서"))
    
    return f"[문서 제목] {title}\n[출처 파일] {doc.get('file', '알 수 없음')}\n[문장 리스트]\n{list_section}\n\n[요청 사항]\n- 공문서 표기는 그대로 유지하고, 오타나 맞춤법 오류만 지적하세요.\n- 각 문장은 meta 정보를 참고해서 의도된 표현인지 판단해 주세요.\n- function result는 아래 JSON schema에 맞춰서 errors 배열만 반환하세요.\n"

def sanitize_response_text(text):
    cleaned = (text or "").strip()
    if cleaned.startswith("```json"):
        cleaned = re.sub(r"^```json\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)
    elif cleaned.startswith("```"):
        cleaned = re.sub(r"^```\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)
    return cleaned

def build_prompt_payload(doc):
    system = SYSTEM_PROMPT
    rag_section = build_rag_prompt_section()
    user = build_user_prompt(doc)
    
    # 시스템 프롬프트에 RAG 지침 추가
    full_system = f"{system}\n{rag_section}" if rag_section else system
    
    combined = f"{full_system}\n\n{user}"
    return {
        "system": full_system,
        "user": user,
        "combined": combined
    }

def call_gemini(prompt_text, api_key, model=MODEL_MAP[PROVIDER_GEMINI]):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
    payload = {
        "contents": [{"parts": [{"text": prompt_text}]}],
        "generationConfig": {
            "responseMimeType": "application/json",
            "temperature": 0,
            "topP": 0.01,
            "topK": 1
        }
    }
    response = requests.post(url, json=payload, headers={"Content-Type": "application/json"})
    if response.status_code != 200:
        raise Exception(f"Gemini request failed ({response.status_code}): {response.text}")
    data = response.json()
    try:
        return data["candidates"][0]["content"]["parts"][0]["text"]
    except (KeyError, IndexError):
        return ""

def call_openai(system_prompt, user_text, api_key, model=MODEL_MAP[PROVIDER_OPENAI]):
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"}
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_text},
        ],
        "temperature": 0,
        "response_format": {"type": "json_object"},
    }
    response = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload)
    if response.status_code != 200:
        raise Exception(f"OpenAI request failed ({response.status_code}): {response.text}")
    return response.json().get("choices", [{}])[0].get("message", {}).get("content", "")

def call_anthropic(system_prompt, user_text, api_key, model=MODEL_MAP[PROVIDER_ANTHROPIC]):
    headers = {
        "Content-Type": "application/json",
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
    }
    payload = {
        "model": model,
        "max_tokens": 8096,
        "temperature": 0,
        "system": system_prompt,
        "messages": [{"role": "user", "content": user_text}],
    }
    response = requests.post("https://api.anthropic.com/v1/messages", headers=headers, json=payload)
    if response.status_code != 200:
        raise Exception(f"Anthropic request failed ({response.status_code}): {response.text}")
    return response.json().get("content", [{}])[0].get("text", "")

def parse_errors(response_text):
    cleaned = sanitize_response_text(response_text)
    if not cleaned:
        return []
    try:
        parsed = json.loads(cleaned)
        return parsed.get("errors", []) if isinstance(parsed.get("errors"), list) else []
    except json.JSONDecodeError as e:
        # 응답이 너무 길어서 잘린 경우 예외를 발생시키지 않고 빈 배열 반환으로 우회 (부분 실패 허용)
        try:
            # 어떻게든 복원 시도 (잘린 JSON의 괄호를 강제로 닫음)
            force_closed = cleaned + '"}]}' if cleaned.endswith('"') else cleaned + '}]}'
            return json.loads(force_closed).get("errors", [])
        except Exception:
            return []  # 도저히 안되면 그냥 패스 (에러로 팝업 중단 방지)

BATCH_SIZE = 50  # 사용자 요청으로 50으로 롤백
MAX_WORKERS = 3

class RateLimitError(Exception):
    pass

def _call_provider(provider, payload, api_key):
    if provider == PROVIDER_OPENAI:
        raw = call_openai(payload["system"], payload["user"], api_key)
    elif provider == PROVIDER_ANTHROPIC:
        raw = call_anthropic(payload["system"], payload["user"], api_key)
    else:
        raw = call_gemini(payload["combined"], api_key)
    return raw

def _is_rate_limit_error(e):
    return "429" in str(e)

def _run_batches_sequential(batches, doc, provider, api_key, progress_callback, total_batches, start_batch_num=1):
    all_errors = []
    for idx, batch in enumerate(batches):
        batch_num = start_batch_num + idx
        if progress_callback:
            progress_callback(batch_num, total_batches)
        partial_doc = {**doc, "sentences": batch}
        payload = build_prompt_payload(partial_doc)
        raw = _call_provider(provider, payload, api_key)
        all_errors.extend(parse_errors(raw))
    return all_errors

def run_ai_check(doc, progress_callback=None):
    sentences = doc.get("sentences", [])
    if not sentences:
        return []

    provider = os.environ.get("TYPO_PROVIDER", PROVIDER_GEMINI)
    api_key = os.environ.get("TYPO_API_KEY")
    if not api_key:
        api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("API key is missing. Please set it in the application settings.")

    batches = [sentences[i:i + BATCH_SIZE] for i in range(0, len(sentences), BATCH_SIZE)]
    total_batches = len(batches)
    completed = [0]

    def run_batch(batch_num, batch):
        partial_doc = {**doc, "sentences": batch}
        payload = build_prompt_payload(partial_doc)
        try:
            raw = _call_provider(provider, payload, api_key)
        except Exception as e:
            if _is_rate_limit_error(e):
                raise RateLimitError(str(e))
            raise
        errors = parse_errors(raw)
        completed[0] += 1
        if progress_callback:
            progress_callback(completed[0], total_batches)
        return batch_num, errors

    # 병렬 시도
    results = {}
    rate_limited_from = None

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(run_batch, i, batch): i for i, batch in enumerate(batches)}
        for future in as_completed(futures):
            try:
                batch_num, errors = future.result()
                results[batch_num] = errors
            except RateLimitError:
                # 429 발생 — 나머지 배치 인덱스 파악 후 순차 처리로 전환
                rate_limited_from = min(
                    idx for idx, f in futures.items() if f not in [ff for ff in results]
                    if idx not in results
                ) if any(idx not in results for idx in futures.values()) else None
                # 실행 중인 future 취소 (이미 시작된 건 못 막음)
                for f in futures:
                    f.cancel()
                break

    # 429 폴백: 아직 처리 안 된 배치 순차 처리
    if rate_limited_from is not None:
        remaining = [(i, batches[i]) for i in range(len(batches)) if i not in results]
        remaining.sort()
        time.sleep(2)  # 잠깐 대기 후 순차 재시도
        for i, batch in remaining:
            if progress_callback:
                progress_callback(completed[0] + 1, total_batches)
            partial_doc = {**doc, "sentences": batch}
            payload = build_prompt_payload(partial_doc)
            raw = _call_provider(provider, payload, api_key)
            results[i] = parse_errors(raw)
            completed[0] += 1

    return [err for i in sorted(results) for err in results[i]]
