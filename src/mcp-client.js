import fs from "fs";
import path from "path";
import { Client } from "@modelcontextprotocol/sdk/client";
import { StdioClientTransport } from "@modelcontextprotocol/sdk/client/stdio.js";
import { buildDocFromParseResult } from "./doc-model.js";

const MCP_COMMAND = process.env.MCP_COMMAND || "npx";
const envArgs = process.env.MCP_ARGS ? process.env.MCP_ARGS.split(" ").filter(Boolean) : null;
const MCP_ARGS = envArgs ?? ["-y", "kordoc-mcp"];

const createTransport = () =>
  new StdioClientTransport({
    command: MCP_COMMAND,
    args: MCP_ARGS,
    stderr: "pipe",
  });

const createClient = () =>
  new Client({
    name: "misspelling-checker",
    version: "0.1.0",
  });

export const parseFileWithMcp = async (filePath) => {
  const resolved = path.resolve(filePath);
  const transport = createTransport();
  const client = createClient();
  try {
    await client.connect(transport);
    const response = await client.callTool({
      name: "parse_document",
      arguments: {
        file_path: resolved,
      },
    });
    if (response.isError) {
      const message = (response.content || [])
        .map((chunk) => chunk.text)
        .filter(Boolean)
        .join("\n");
      throw new Error(`MCP parse_document failed: ${message}`);
    }
    const structured = response.structuredContent;
    if (!structured) {
      throw new Error("MCP 응답에 structuredContent가 없습니다.");
    }
    return buildDocFromParseResult(structured, resolved);
  } finally {
    await transport.close();
  }
};

if (process.argv[1].endsWith("mcp-client.js")) {
  const args = process.argv.slice(2);
  const fileArgIndex = args.findIndex((arg) => !arg.startsWith("-"));
  const targetFile = args[fileArgIndex];
  const outputIndex = args.findIndex((arg) => arg === "--out" || arg === "-o");
  const output = outputIndex >= 0 ? args[outputIndex + 1] : null;
  if (!targetFile || !output) {
    console.error("Usage: node src/mcp-client.js <file> --out output.json");
    process.exit(1);
  }
  parseFileWithMcp(targetFile)
    .then((doc) => {
      fs.writeFileSync(output, JSON.stringify(doc, null, 2), "utf-8");
      console.log(`MCP 파싱 결과 저장: ${output}`);
    })
    .catch((err) => {
      console.error(err);
      process.exit(1);
    });
}
