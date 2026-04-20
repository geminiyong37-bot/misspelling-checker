# -*- coding: utf-8 -*-
import os

file_path = r'c:\antigravity\misspelling checker\src\ai_client.py'

with open(file_path, 'rb') as f:
    raw_data = f.read()

content = raw_data.decode('utf-8')

# 1. 精교화된 Spacing Rule 반영
new_spacing_rules = """- **띄어쓰기 오탐 방지 및 정교화**: 
    - **명백한 오류만 지적**: 단어와 단어 사이의 명백한 띄어쓰기 누락(예: '책상을정리하다' -> '책상을 정리하다')만 지적합니다.
    - **복합 명사 및 합성어 허용**: '복합 명사', '전문 용어', '행정 용어' 등은 붙여 쓰는 것이 가독성에 도움이 되거나 일상적으로 허용되므로 띄어쓰기 수정을 제안하지 마세요. (예: '계획수립', '결과보고', '데이터분석' 등은 그대로 두세요)
    - **표준어 보존**: '횟수', '개수', '건수', '점수' 등은 그 자체로 하나의 명사이므로 무조건 붙여 쓰세요.
    - **표/서식 데이터**: 표 내부 텍스트나 meta에 "의도적서식"이 포함된 문장은 띄어쓰기 오류를 지적하지 마세요."""

# 기존 띄어쓰기 관련 규칙들을 찾아서 교체
old_part_start = "- 표 텍스트는 셀 간 경계가 불분명하므로 단어가 붙어 있어도 그대로 두세요."
old_part_end = " 그대로 존중하세요."

if old_part_start in content:
    # 대략적인 리스트 부분을 새 규칙으로 교체
    start_idx = content.find(old_part_start)
    # '존중하세요.' 뒤의 행 끝까지 찾기
    end_marker = "존중하세요."
    end_idx = content.find(end_marker, start_idx) + len(end_marker)
    
    content = content[:start_idx] + new_spacing_rules + content[end_idx:]

# 2. JSON Schema에서 spacing 다시 활성화 (사용자가 원하므로)
if '"errorType": "spelling | grammar"' in content:
    content = content.replace('"errorType": "spelling | grammar"', '"errorType": "spelling | spacing | grammar"')

with open(file_path, 'wb') as f:
    f.write(content.encode('utf-8'))

print("Updated spacing logic with refinement.")
