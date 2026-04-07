import ExcelJS from "exceljs";
import fs from "fs";
import path from "path";
import { describeSentence } from "./doc-model.js";
import { loadAiResult, aiErrorsToRows } from "./ai-result-utils.js";

const FILE_COLORS = [
  "FFDBEAFE",
  "FFFEF3C7",
  "FFD1FAE5",
  "FFFCE7F3",
  "FFE0E7FF",
  "FFFED7AA",
  "FFE5E7EB",
  "FFDDD6FE",
  "FFCFFAFE",
  "FFFECACA",
];

const ORANGE_FILL = {
  type: "pattern",
  pattern: "solid",
  fgColor: { argb: "FFE699" },
};

const HEADER_FILL = {
  type: "pattern",
  pattern: "solid",
  fgColor: { argb: "374151" },
};

const getArgs = () => {
  const argv = process.argv.slice(2);
  const result = {
    input: null,
    output: null,
    ai: null,
  };
  for (let i = 0; i < argv.length; i++) {
    const key = argv[i];
    if ((key === "--input" || key === "-i") && argv[i + 1]) {
      result.input = argv[++i];
    } else if ((key === "--output" || key === "-o") && argv[i + 1]) {
      result.output = argv[++i];
    } else if ((key === "--ai" || key === "-a") && argv[i + 1]) {
      result.ai = argv[++i];
    }
  }
  return result;
};

const loadDocument = (filePath) => {
  const absolute = path.resolve(filePath);
  const raw = fs.readFileSync(absolute, "utf-8");
  return JSON.parse(raw);
};

const buildRowsFromDoc = (doc) => {
  if (!doc.sentences) return [];
  const source = doc.file ?? doc.source ?? "알 수 없는 문서";
  return doc.sentences.map((sentence, index) => ({
    file: source,
    page: sentence.pageNumber ?? 1,
    original: sentence.text ?? "",
    corrected: "",
    help: sentence.meta ?? describeSentence(sentence),
    index: index + 1,
  }));
};

const createWorkbook = (rows) => {
  const workbook = new ExcelJS.Workbook();
  const sheet = workbook.addWorksheet("오타검토결과");

  const headers = ["문서명", "수정전", "수정후", "비고"];
  sheet.addRow(headers);

  // 너비 설정 (사용자 요청 반영)
  const defaultWidths = [30, 20, 20, 40];
  sheet.columns = defaultWidths.map((w) => ({ width: w }));

  // 헤더 스타일
  sheet.getRow(1).eachCell((cell) => {
    cell.font = { bold: true, color: { argb: "FFFFFFFF" } };
    cell.fill = HEADER_FILL;
    cell.alignment = { horizontal: "center" };
  });

  const combinationCounts = rows.reduce((acc, row) => {
    const key = `${row.file}|${row.page}|${row.original}`;
    acc[key] = (acc[key] || 0) + 1;
    return acc;
  }, {});

  const fileColorMap = new Map();
  let colorIdx = 0;

  rows.forEach((row) => {
    const original = row.original;
    const corrected = row.corrected;
    const note = row.help;
    const key = `${row.file}|${row.page}|${original}`;
    const repeated = combinationCounts[key] ?? 1;
    const noteText = repeated > 1 ? `[중복 ${repeated}회] ${note}`.trim() : note;

    // 문서명: 파일명만 (basename)
    const displayName = path.basename(row.file);

    // 파일별 색상 할당
    if (!fileColorMap.has(displayName)) {
      fileColorMap.set(displayName, FILE_COLORS[colorIdx % FILE_COLORS.length]);
      colorIdx++;
    }
    const fileBgColor = fileColorMap.get(displayName);

    const excelRow = [displayName, original, corrected, noteText];
    const inserted = sheet.addRow(excelRow);

    const normalizedOriginal = (original ?? "").replace(/\s+/g, "");
    const normalizedCorrected = (corrected ?? "").replace(/\s+/g, "");

    // 오타가 있는 행 강조
    if (normalizedCorrected && normalizedOriginal !== normalizedCorrected) {
      const fill = {
        type: "pattern",
        pattern: "solid",
        fgColor: { argb: fileBgColor },
      };
      inserted.getCell(2).fill = fill; // 수정전
      inserted.getCell(3).fill = fill; // 수정후
    }
  });

  return workbook;
};

const run = async () => {
  const { input, output, ai } = getArgs();
  if ((!input && !ai) || !output) {
    console.error("Usage: node src/export-excel.js (--input parsed.json | --ai ai-errors.json) --output parsed.xlsx");
    process.exit(1);
  }

  const doc = ai ? loadAiResult(ai) : loadDocument(input);
  const rows = ai ? aiErrorsToRows(doc) : buildRowsFromDoc(doc);
  const workbook = createWorkbook(rows);
  await workbook.xlsx.writeFile(output);
  console.log(`Excel 저장 완료: ${output}`);
};

run().catch((err) => {
  console.error(err);
  process.exit(1);
});
