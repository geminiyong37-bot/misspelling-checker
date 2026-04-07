import fs from "fs";
import path from "path";
import { markdownToHwpx } from "kordoc";
import { describeSentence } from "./doc-model.js";

const parseArgs = () => {
  const argv = process.argv.slice(2);
  const result = { input: null, output: null };
  for (let i = 0; i < argv.length; i++) {
    const key = argv[i];
    if ((key === "--input" || key === "-i") && argv[i + 1]) {
      result.input = argv[++i];
    } else if ((key === "--output" || key === "-o") && argv[i + 1]) {
      result.output = argv[++i];
    }
  }
  return result;
};

const loadDocument = (filePath) => {
  const absolute = path.resolve(filePath);
  const raw = fs.readFileSync(absolute, "utf-8");
  return JSON.parse(raw);
};

const buildRows = (doc) => {
  return (doc.sentences || []).map((sentence, index) => ({
    index: index + 1,
    original: sentence.text?.replace(/\|/g, "\\|").replace(/\r?\n/g, " ") ?? "",
    corrected: "",
    note: describeSentence(sentence),
  }));
};

const buildMarkdownTable = (doc, rows) => {
  const title = `# 오타 검출 리포트\n\n문서명: ${doc.file}\n\n`;
  const header = "| 연번 | 수정전 | 수정후 | 비고 |\n| --- | --- | --- | --- |";
  const body = rows
    .map(
      (row) =>
        `| ${row.index} | ${row.original} | ${row.corrected} | ${row.note} |`
    )
    .join("\n");
  return `${title}${header}\n${body}`;
};

const run = async () => {
  const { input, output } = parseArgs();
  if (!input || !output) {
    console.error("Usage: node src/export-hwpx.js --input parsed.json --output output.hwpx");
    process.exit(1);
  }

  const doc = loadDocument(input);
  const rows = buildRows(doc);
  const markdown = buildMarkdownTable(doc, rows);
  const buffer = await markdownToHwpx(markdown);
  fs.writeFileSync(path.resolve(output), Buffer.from(buffer));
  console.log(`HWPX 저장 완료: ${output}`);
};

run().catch((err) => {
  console.error(err);
  process.exit(1);
});
