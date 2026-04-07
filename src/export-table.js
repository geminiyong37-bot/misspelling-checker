import fs from "fs";
import path from "path";
import { describeSentence } from "./doc-model.js";
import { loadAiResult, aiErrorsToRows } from "./ai-result-utils.js";

const parseArgs = () => {
  const argv = process.argv.slice(2);
  const result = { input: null, output: null, ai: null };
  for (let i = 0; i < argv.length; i++) {
    if ((argv[i] === "--input" || argv[i] === "-i") && argv[i + 1]) {
      result.input = argv[++i];
      continue;
    }
    if ((argv[i] === "--output" || argv[i] === "-o") && argv[i + 1]) {
      result.output = argv[++i];
      continue;
    }
    if ((argv[i] === "--ai" || argv[i] === "-a") && argv[i + 1]) {
      result.ai = argv[++i];
      continue;
    }
  }
  return result;
};

const loadDocument = (filePath) => {
  const content = fs.readFileSync(path.resolve(filePath), "utf-8");
  return JSON.parse(content);
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

const makeTable = (rows) => {
  if (rows.length === 0) {
    return "문장 데이터가 없습니다.";
  }

  const header = "| 연번 | 수정전 | 수정후 | 비고 |\n| --- | --- | --- | --- |";
  const body = rows
    .map((row, index) => {
      const original = (row.original ?? row.text ?? "")
        .replace(/\|/g, "\\|")
        .replace(/\r?\n/g, " ");
      const reason = row.help ?? row.meta ?? describeSentence(row);
      const seq = row.index ?? index + 1;
      return `| ${seq} | ${original} | ${row.corrected ?? ""} | ${reason} |`;
    })
    .join("\n");

  return header + "\n" + body;
};

const run = () => {
  const { input, output, ai } = parseArgs();
  if (!input && !ai) {
    console.error("Usage: node src/export-table.js --input parsed.json | --ai ai-errors.json [--output table.md]");
    process.exit(1);
  }

  let doc;
  if (ai) {
    doc = loadAiResult(ai);
  } else {
    doc = loadDocument(input);
  }
  const rows = ai ? aiErrorsToRows(doc) : buildRowsFromDoc(doc);
  const table = makeTable(rows);
  const prefixTarget = doc.file ?? doc.source ?? (ai ? doc.source ?? "AI 결과" : "문서");
  const prefix = `파일명: ${prefixTarget}\n\n`;
  const payload = prefix + table + "\n";
  if (output) {
    fs.writeFileSync(output, payload, "utf-8");
    console.log(`표 출력 완료: ${output}`);
  } else {
    console.log(payload);
  }
};

run();
