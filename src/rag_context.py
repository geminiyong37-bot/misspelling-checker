import os

import sys

def resource_path(relative):
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative)
    base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_path, relative)

RAG_DOC_PATH = resource_path(os.path.join("docs", "공문서_지침_압축.txt"))

def normalize_text(value):
    if not value:
        return ""
    # 은어/개행 처리 및 공백 제거
    lines = value.replace("\r\n", "\n").split("\n")
    return "\n".join([line.strip() for line in lines if line.strip()])

def get_rag_instruction_text():
    if not os.path.exists(RAG_DOC_PATH):
        print(f"경고: RAG 지침 파일을 찾을 수 없습니다: {RAG_DOC_PATH}")
        return ""
    
    try:
        with open(RAG_DOC_PATH, "r", encoding="utf-8") as f:
            raw = f.read()
        return normalize_text(raw)
    except Exception as e:
        print(f"오류: RAG 파일을 읽는 중 문제가 발생했습니다: {e}")
        return ""

def build_rag_prompt_section():
    text = get_rag_instruction_text()
    if not text:
        return ""
    return f"\n[참고: 공문서 작성 지침]\n{text}\n"
