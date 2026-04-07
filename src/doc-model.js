const SENTENCE_SPLIT_REGEX = /(?<=[.?!])\s+|(?<=\S)\r?\n+/;

const escapeOrEmpty = (value) => (value ?? "").trim();

const splitTextIntoSentences = (text) => {
  if (!text) {
    return [];
  }
  return text
    .split(SENTENCE_SPLIT_REGEX)
    .map((chunk) => chunk.trim())
    .filter((chunk) => chunk.length > 0);
};

const summarizeTable = (table, pipeChar = " | ") => {
  if (!table || !Array.isArray(table.cells)) {
    return null;
  }
  return {
    rows: table.cells.map((row, rowIndex) => ({
      rowIndex,
      cells: row.map((cell, columnIndex) => ({
        rowIndex,
        columnIndex,
        text: escapeOrEmpty(cell.text),
        colSpan: cell.colSpan || 1,
        rowSpan: cell.rowSpan || 1,
        isHeader: rowIndex === 0 && table.hasHeader,
      })),
    })),
    hasHeader: Boolean(table.hasHeader),
  };
};

export const structureBlock = (block) => {
  const baseText = escapeOrEmpty(block.text);
  const structured = {
    type: block.type || "paragraph",
    text: baseText,
    pageNumber: block.pageNumber || 1,
    headingLevel: block.level,
    style: block.style,
    href: block.href,
    footnote: block.footnoteText,
    table: block.table ? summarizeTable(block.table) : null,
    image: block.imageData
      ? {
        filename: block.imageData.filename,
        mimeType: block.imageData.mimeType,
      }
      : null,
  };
  return structured;
};

export const collectPages = (blocks) => {
  const pageMap = new Map();
  for (const block of blocks) {
    const structured = structureBlock(block);
    const pageNumber = structured.pageNumber || 1;
    if (!pageMap.has(pageNumber)) {
      pageMap.set(pageNumber, []);
    }
    pageMap.get(pageNumber).push(structured);
  }
  return Array.from(pageMap.entries())
    .sort((a, b) => a[0] - b[0])
    .map(([number, blockList]) => ({
      number,
      blocks: blockList,
      text: blockList.map((b) => b.text).filter(Boolean).join("\n\n"),
    }));
};

export const describeSentence = (sentence) => {
  const parts = [];
  if (sentence.blockType) {
    parts.push(
      sentence.blockType === "heading"
        ? `heading ${sentence.headingLevel ?? 1}`
        : `block ${sentence.blockType}`
    );
  }
  if (sentence.blockTable?.hasHeader) {
    parts.push("table(헤더 포함)");
  } else if (sentence.blockTable) {
    parts.push("table");
  }
  if (sentence.blockFootnote) {
    parts.push(`각주: ${sentence.blockFootnote}`);
  }
  if (sentence.blockHref) {
    parts.push(`링크: ${sentence.blockHref}`);
  }
  return parts.length > 0 ? parts.join(" | ") : "본문";
};

const attachMeta = (sentence) => ({
  ...sentence,
  meta: describeSentence(sentence),
});

export const buildSentenceUnits = (pages) => {
  return pages.flatMap((page) =>
    page.blocks.flatMap((block, blockIndex) => {
      const units = [];

      // 블록 자체의 텍스트 처리 (paragraph, heading 등)
      if (block.text) {
        splitTextIntoSentences(block.text).map((sentence, sentenceIndex) => {
          units.push(attachMeta({
            text: sentence,
            pageNumber: page.number,
            blockType: block.type,
            headingLevel: block.headingLevel,
            blockFootnote: block.footnote,
            blockTable: block.table,
            blockHref: block.href,
            blockIndex,
            sentenceIndex,
          }));
        });
      }

      // 표(table) 블록 처리: 셀 내용이 block.text에 포함되지 않으므로 개별 추출
      if (block.table && block.table.rows) {
        block.table.rows.forEach((row, rowIndex) => {
          row.cells.forEach((cell, cellIndex) => {
            if (cell.text) {
              splitTextIntoSentences(cell.text).forEach((sentence, sentenceIndex) => {
                units.push(attachMeta({
                  text: sentence,
                  pageNumber: page.number,
                  blockType: "table-cell",
                  blockTable: block.table,
                  rowIndex,
                  cellIndex,
                  blockIndex,
                  sentenceIndex,
                }));
              });
            }
          });
        });
      }

      return units;
    })
  );
};


export const buildDocFromParseResult = (parseResult, filePath) => {
  const pages = collectPages(parseResult.blocks || []);
  const sentences = buildSentenceUnits(pages);
  return {
    file: filePath,
    fileType: parseResult.fileType,
    metadata: parseResult.metadata ?? null,
    outline: parseResult.outline ?? [],
    warnings: parseResult.warnings ?? [],
    isImageBased: Boolean(parseResult.isImageBased),
    pageCount: parseResult.pageCount ?? pages.length,
    markdown: parseResult.markdown,
    pages,
    sentences,
    source: parseResult.filePath ?? filePath,
  };
};
