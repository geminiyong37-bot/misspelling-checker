import fs from "fs";
import path from "path";

const RAG_DOC_PATH = path.resolve("docs", "공문서_지침_압축.txt");

const normalizeText = (value) =>
  value
    .replace(/\r\n/g, "\n")
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean)
    .join("\n");

export const getRagInstructionText = () => {
  if (!fs.existsSync(RAG_DOC_PATH)) {
    return "";
  }
  const raw = fs.readFileSync(RAG_DOC_PATH, "utf-8");
  return normalizeText(raw);
};

export const buildRagPromptSection = () => {
  const text = getRagInstructionText();
  if (!text) {
    return "";
  }
  return `다음 규칙을 반드시 따라 작성하세요:\n${text}`;
};
