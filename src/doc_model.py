import re
import os

SENTENCE_SPLIT_REGEX = re.compile(r"(?<=[.?!])\s+|(?<=\S)\r?\n+")

def escape_or_empty(value):
    return (str(value) if value is not None else "").strip()

def split_text_into_sentences(text):
    if not text:
        return []
    chunks = SENTENCE_SPLIT_REGEX.split(text)
    return [c.strip() for c in chunks if c.strip()]

def summarize_table(table):
    if not table or "cells" not in table:
        return None
    
    rows = []
    cells_data = table.get("cells", [])
    has_header = table.get("hasHeader", False)
    
    for row_idx, row in enumerate(cells_data):
        row_cells = []
        for col_idx, cell in enumerate(row):
            row_cells.append({
                "rowIndex": row_idx,
                "columnIndex": col_idx,
                "text": escape_or_empty(cell.get("text")),
                "colSpan": cell.get("colSpan", 1),
                "rowSpan": cell.get("rowSpan", 1),
                "isHeader": row_idx == 0 and has_header
            })
        rows.append({"rowIndex": row_idx, "cells": row_cells})
        
    return {
        "rows": rows,
        "hasHeader": bool(has_header)
    }

def structure_block(block):
    base_text = escape_or_empty(block.get("text"))
    table_data = block.get("table")
    image_data = block.get("imageData")
    
    return {
        "type": block.get("type", "paragraph"),
        "text": base_text,
        "pageNumber": block.get("pageNumber", 1),
        "headingLevel": block.get("level"),
        "style": block.get("style"),
        "href": block.get("href"),
        "footnote": block.get("footnoteText"),
        "table": summarize_table(table_data) if table_data else None,
        "image": {
            "filename": image_data.get("filename"),
            "mimeType": image_data.get("mimeType")
        } if image_data else None
    }

def collect_pages(blocks):
    page_map = {}
    for block in blocks:
        structured = structure_block(block)
        page_num = structured.get("pageNumber", 1)
        if page_num not in page_map:
            page_map[page_num] = []
        page_map[page_num].append(structured)
        
    sorted_pages = sorted(page_map.items())
    result = []
    for num, block_list in sorted_pages:
        texts = [b["text"] for b in block_list if b["text"]]
        result.append({
            "number": num,
            "blocks": block_list,
            "text": "\n\n".join(texts)
        })
    return result

def is_char_spaced(text):
    """글자 단위 띄어쓰기 여부 감지 (예: '자 격 요 건')"""
    if not text or len(text) < 3:
        return False
    tokens = text.split(" ")
    if len(tokens) < 2:
        return False
    single_char_count = sum(1 for t in tokens if len(t) == 1)
    return single_char_count / len(tokens) >= 0.7

def describe_sentence(sentence):
    parts = []
    block_type = sentence.get("blockType")
    if block_type:
        if block_type == "heading":
            parts.append(f"heading {sentence.get('headingLevel', 1)}")
        else:
            parts.append(f"block {block_type}")
            
    table = sentence.get("blockTable")
    if table:
        if table.get("hasHeader"):
            parts.append("table(헤더 포함)")
        else:
            parts.append("table")
            
    if sentence.get("charSpaced"):
        parts.append("글자단위띄어쓰기(의도적서식)")

    fn = sentence.get("blockFootnote")
    if fn:
        parts.append(f"각주: {fn}")
        
    href = sentence.get("blockHref")
    if href:
        parts.append(f"링크: {href}")
        
    return " | ".join(parts) if parts else "본문"

def attach_meta(sentence):
    sentence["meta"] = describe_sentence(sentence)
    return sentence

def build_sentence_units(pages):
    units = []
    for page in pages:
        for b_idx, block in enumerate(page["blocks"]):
            # Text blocks
            if block.get("text"):
                sentences = split_text_into_sentences(block["text"])
                for s_idx, s_text in enumerate(sentences):
                    units.append(attach_meta({
                        "text": s_text,
                        "pageNumber": page["number"],
                        "blockType": block["type"],
                        "headingLevel": block.get("headingLevel"),
                        "blockFootnote": block.get("footnote"),
                        "blockTable": block.get("table"),
                        "blockHref": block.get("href"),
                        "blockIndex": b_idx,
                        "sentenceIndex": s_idx
                    }))
            
            # Table blocks
            table = block.get("table")
            if table and table.get("rows"):
                for r_idx, row in enumerate(table["rows"]):
                    for c_idx, cell in enumerate(row["cells"]):
                        cell_text = cell.get("text")
                        if cell_text:
                            sentences = split_text_into_sentences(cell_text)
                            for s_idx, s_text in enumerate(sentences):
                                units.append(attach_meta({
                                    "text": s_text,
                                    "pageNumber": page["number"],
                                    "blockType": "table-cell",
                                    "blockTable": table,
                                    "rowIndex": r_idx,
                                    "cellIndex": c_idx,
                                    "blockIndex": b_idx,
                                    "sentenceIndex": s_idx,
                                    "charSpaced": is_char_spaced(s_text)
                                }))
    return units

def build_doc_from_parse_result(parse_result, file_path):
    blocks = parse_result.get("blocks", [])
    pages = collect_pages(blocks)
    sentences = build_sentence_units(pages)
    
    return {
        "file": file_path,
        "fileType": parse_result.get("fileType"),
        "metadata": parse_result.get("metadata"),
        "outline": parse_result.get("outline", []),
        "warnings": parse_result.get("warnings", []),
        "isImageBased": bool(parse_result.get("isImageBased")),
        "pageCount": parse_result.get("pageCount", len(pages)),
        "markdown": parse_result.get("markdown"),
        "pages": pages,
        "sentences": sentences,
        "source": parse_result.get("filePath", file_path)
    }
