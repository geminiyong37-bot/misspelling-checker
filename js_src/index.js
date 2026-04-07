import fs from "fs";
import path from "path";
import { parse as cliParse } from "../../dist/index.js";
import { buildDocFromParseResult } from "./doc-model.js";
import { parseFileWithMcp } from "./mcp-client.js";

const parseArgs = () => {
  const args = process.argv.slice(2);
  const files = [];
  let output = null;
  let useMcp = false;

  for (let i = 0; i < args.length; i++) {
    const arg = args[i];
    if (arg === "--out" && args[i + 1]) {
      output = args[++i];
    } else if (arg === "--mcp" || arg === "--use-mcp") {
      useMcp = true;
    } else if (!arg.startsWith("-")) {
      files.push(arg);
    }
  }

  return { files, output, useMcp };
};

const parseWithCli = async (filePath) => {
  const result = await cliParse(filePath);
  if (!result.success) {
    throw new Error(result.error || "파싱 실패");
  }
  const resolved = path.resolve(filePath);
  return buildDocFromParseResult({ ...result, filePath: resolved }, resolved);
};

const run = async () => {
  const { files, output, useMcp } = parseArgs();
  if (files.length === 0) {
    console.error("Usage: node src/index.js [--mcp] <file> [--out output.json]");
    process.exit(1);
  }

  for (const file of files) {
    try {
      const doc = useMcp ? await parseFileWithMcp(file) : await parseWithCli(file);
      const payload = JSON.stringify(doc, null, 2);
      if (output) {
        fs.writeFileSync(output, payload, "utf-8");
        console.log(`Parsed ${file} → ${output}`);
      } else {
        console.log(payload);
      }
    } catch (error) {
      console.error(`Unable to parse ${file}: ${error?.message || error}`);
      process.exitCode = 1;
    }
  }
};

run().catch((err) => {
  console.error(err);
  process.exit(1);
});
