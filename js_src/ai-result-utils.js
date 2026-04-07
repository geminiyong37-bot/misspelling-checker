import fs from "fs";
import path from "path";

export const loadAiResult = (filePath) => {
  const absolute = path.resolve(filePath);
  const raw = fs.readFileSync(absolute, "utf-8");
  const parsed = JSON.parse(raw);
  return parsed;
};

export const aiErrorsToRows = (aiResult) => {
  const source = aiResult.source || aiResult.metadata?.title || "알 수 없는 문서";
  const errors = Array.isArray(aiResult.errors) ? aiResult.errors : [];
  return errors.map((error, index) => {
    // "맞춤법 오류: ", "띄어쓰기 오류: " 등 접두사 제거
    let reason = error.reason || error.meta || "설명 없음";
    reason = reason.replace(/^(맞춤법|띄어쓰기|표기|문장)\s*오류:\s*/, "");

    return {
      file: source,
      page: error.page ?? "",
      original: error.original ?? error.originalText ?? "",
      corrected: error.corrected ?? error.correctedText ?? "",
      help: reason,
      meta: error.meta,
      index: index + 1,
    };
  });
};

