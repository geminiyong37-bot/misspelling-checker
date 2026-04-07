import fs from "fs";
import path from "path";
import { runGeminiCheck, buildAiPrompt } from "./ai-client.js";

const parseArgs = () => {
  const argv = process.argv.slice(2);
  const result = { input: null, output: null };
  for (let i = 0; i < argv.length; i++) {
    if ((argv[i] === "--input" || argv[i] === "-i") && argv[i + 1]) {
      result.input = argv[++i];
      continue;
    }
    if ((argv[i] === "--output" || argv[i] === "-o") && argv[i + 1]) {
      result.output = argv[++i];
      continue;
    }
  }
  return result;
};

const loadDocument = (filePath) => {
  const absolute = path.resolve(filePath);
  const raw = fs.readFileSync(absolute, "utf-8");
  return JSON.parse(raw);
};

const run = async () => {
  const { input, output } = parseArgs();
  if (!input) {
    console.error("Usage: node src/ai-check.js --input parsed.json [--output ai-errors.json]");
    process.exit(1);
  }

  const doc = loadDocument(input);
  console.log("AI 프롬프트 생성 중…");
  const prompt = buildAiPrompt(doc);
  console.log("Gemini 호출 중… (응답 대기)");
  try {
    const errors = await runGeminiCheck(doc);
    const payload = {
      source: doc.file,
      metadata: doc.metadata,
      errors,
      generatedAt: new Date().toISOString(),
    };
    if (output) {
      fs.writeFileSync(path.resolve(output), JSON.stringify(payload, null, 2), "utf-8");
      console.log(`AI 결과 저장 완료: ${output}`);
    } else {
      console.log(JSON.stringify(payload, null, 2));
    }
  } catch (err) {
    console.error("AI 검사 중 오류 발생:", err.message);
    console.error(err);
    process.exit(1);
  }
};

run();
