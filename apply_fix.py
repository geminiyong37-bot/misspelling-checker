import os

file_path = r'c:\antigravity\misspelling checker\src\ai_client.py'

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Prompt modification
old_prompt_part = """- 표 텍스트는 셀 간 경계가 불분명하므로 단어가 붙어 있어도 그대로 두세요.
- **표준어 보존 및 오탐 방지**: '횟수', '개수', '건수', '점수' 등은 그 자체로 하나의 명사입니다. '회 수'와 같이 띄어 쓰라는 지적은 명백한 오탐이므로 절대 하지 마세요.
- 의존 명사(수, 것, 데 등)로 의심되더라도, 단어가 사전에 한 단어(명사)로 등록되어 있다면 띄어쓰기 수정을 제안하지 마세요.
- meta에 "글자단위띄어쓰기(의도적서식)"가 포함된 문장은 가독성을 위한 의도적 서식이므로 어떤 오류도 지적하지 마세요.
- **외래어 표기법 지적 금지**: 외래어 표기법에 따른 수정 제안(예: '컨텐츠' → '콘텐츠', '디지탈' → '디지털', '스케쥴' → '스케줄' 등)은 절대 하지 마세요. 사용자가 작성한 외래어 표기를 그대로 존중하세요."""

new_prompt_part = """- **띄어쓰기(Spacing) 지적 절대 금지**: 모든 종류의 띄어쓰기 오류를 무시하세요. 단어가 붙어 있거나 잘못 띄어 있어도 절대로 수정 제안을 하지 마세요. 오직 맞춤법(Spelling)과 문법(Grammar) 오류만 검사하세요.
- 표 텍스트는 셀 간 경계가 불분명하므로 단어가 붙어 있어도 그대로 두세요.
- **표준어 보존 및 오탐 방지**: '횟수', '개수', '건수', '점수' 등은 그 자체로 하나의 명사입니다.
- meta에 "글자단위띄어쓰기(의도적서식)"가 포함된 문장은 어떤 오류도 지적하지 마세요.
- **외래어 표기법 지적 금지**: 외래어 표기법에 따른 수정 제안은 절대 하지 마세요."""

content = content.replace(old_prompt_part, new_prompt_part)

# 2. JSON Schema definition update
content = content.replace('"errorType": "spelling | spacing | grammar"', '"errorType": "spelling | grammar"')
content = content.replace('오류가 없으면 {"errors": []} 을 반환하세요.', '오류가 없거나 띄어쓰기 오류만 있는 경우 {"errors": []} 을 반환하세요.')

# 3. Filtering logic update
old_filter = """    try:
        data = json.loads(raw_text)
        errors = data.get("errors", [])
        # 중복 제거 또는 간단한 후처리 가능
        return [e for e in errors if e.get("original") != e.get("corrected")]
    except Exception:
        return []"""

new_filter = """    try:
        data = json.loads(raw_text)
        errors = data.get("errors", [])
        
        filtered_errors = []
        for e in errors:
            # spacing 타입 제거 및 실제 글자 변화가 없는 경우 제외
            if e.get("error_type") == "spacing" or e.get("errorType") == "spacing":
                continue
            if e.get("original") == e.get("corrected"):
                continue
            # corrected와 original의 공백을 제거했을 때 같다면 띄어쓰기 오류로 간주하고 제외
            orig_no_space = (e.get("original") or "").replace(" ", "").replace("\\t", "").strip()
            corr_no_space = (e.get("corrected") or "").replace(" ", "").replace("\\t", "").strip()
            if orig_no_space == corr_no_space:
                continue
                
            filtered_errors.append(e)
            
        return filtered_errors
    except Exception:
        return []"""

content = content.replace(old_filter, new_filter)

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("Successfully updated ai_client.py")
