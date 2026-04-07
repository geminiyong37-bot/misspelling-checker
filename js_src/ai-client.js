import fs from "fs";
import path from "path";

const GEMINI_MODEL = "gemini-2.5-flash";
const GEMINI_API_KEY_ENV = process.env.GEMINI_API_KEY || process.env.TYPING_GEMINI_KEY;
const DEFAULT_GEMINI_KEY = ""; // Removed for security

const SYSTEM_PROMPT = `당신은 대한민국 최고의 맞춤법, 띄어쓰기 및 공문서 작성 전문가입니다.
오직 다음 항목만 찾아주시고, 반드시 순수 JSON(errors 배열)만 출력하세요.

[오타 검출 규칙]
1. 단순 맞춤법/철자 오류 (예: '됬다' → '됐다', '않습니다' → '안 합니다')
2. 띄어쓰기 오류 (예: '국민은행입구' → '국민은행 입구')
3. 개조식/표 안에서 문맥상 명백한 오타 (예: '예산잔액' vs '예산 잔액')

[반드시 제외할 항목]
- 연도 표기 시 ' ('24년, '25년 등) 표현은 정상적인 줄임표 표현이므로 수정하지 마세요.
- 개조식 문단(□, ○, -, · 등)은 현재 상태 그대로 놔두세요.
- HTML 엔티티(&amp;#, &lt; 등)는 깨진 문자열로 간주하지 않고 무시하세요.
- 고유명사/기관명/법령명은 수정하지 마세요.
- 숫자/금액/날짜 표기 방식 차이는 정상 표현입니다.
- 괄호 레이블 뒤의 콜론(:) 유무, 가운데점(·) 의존도, 천 단위 쉼표 차이는 오타가 아닙니다.
- 표 텍스트는 셀 간 경계가 불분명하므로 단어가 붙어 있어도 그대로 두세요.

[출력 JSON 스키마 - 반드시 이 필드명을 사용하세요]
{
  "errors": [
    {
      "page": 1,
      "sentence": "오류가 포함된 전체 문장",
      "original": "수정 전 오류 표현",
      "corrected": "수정 후 올바른 표현",
      "reason": "오류 이유 설명",
      "errorType": "spelling | spacing | grammar"
    }
  ]
}
오류가 없으면 {"errors": []} 을 반환하세요.
`;

const buildUserPrompt = (doc) => {
  const lines = (doc.sentences || []).map((sentence, idx) => {
    const text = (sentence.text || "").replace(/\s+/g, " ").replace(/"/g, '\\"');
    const meta = sentence.meta ? sentence.meta.replace(/\|/g, "\\|") : "meta 없음";
    return `${idx + 1}. text="${text}" | meta="${meta}" | page=${sentence.pageNumber ?? "?"}`;
  });
  const listSection = lines.length > 0 ? lines.join("\n") : "검사할 문장이 없습니다.";
  const title = doc.metadata?.title || path.basename(doc.file || "문서");
  return `[문서 제목] ${title}\n[출처 파일] ${doc.file || "알 수 없음"}\n[문장 리스트]\n${listSection}\n\n[요청 사항]\n- 공문서 표기는 그대로 유지하고, 오타나 맞춤법 오류만 지적하세요.\n- 각 문장은 meta 정보를 참고해서 의도된 표현인지 판단해 주세요.\n- function result는 아래 JSON schema에 맞춰서 errors 배열만 반환하세요.\n`;
};

const sanitizeResponseText = (text) => {
  let cleaned = text?.trim() ?? "";
  if (cleaned.startsWith("```json")) {
    cleaned = cleaned.replace(/^```json\s*/, "").replace(/\s*```$/, "");
  } else if (cleaned.startsWith("```")) {
    cleaned = cleaned.replace(/^```\s*/, "").replace(/\s*```$/, "");
  }
  return cleaned;
};

const buildPromptPayload = (doc) => {
  const system = SYSTEM_PROMPT;
  const user = buildUserPrompt(doc);
  const combined = `${system}\n\n${user}`;
  return {
    system,
    user,
    combined,
  };
};

const callGemini = async (promptText, apiKey = GEMINI_API_KEY_ENV || DEFAULT_GEMINI_KEY) => {
  if (!apiKey) {
    throw new Error("Gemini API key is missing. Set GEMINI_API_KEY environment variable.");
  }
  const url = `https://generativelanguage.googleapis.com/v1beta/models/${GEMINI_MODEL}:generateContent?key=${apiKey}`;
  const payload = {
    contents: [{ parts: [{ text: promptText }] }],
    generationConfig: {
      responseMimeType: "application/json",
      temperature: 0,
      topP: 0.01,
      topK: 1,
    },
  };
  const response = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    const body = await response.text();
    throw new Error(`Gemini request failed (${response.status}): ${body}`);
  }
  const json = await response.json();
  return json?.candidates?.[0]?.content?.parts?.[0]?.text ?? "";
};

const parseErrors = (responseText) => {
  const cleaned = sanitizeResponseText(responseText);
  if (!cleaned) {
    return [];
  }
  try {
    const parsed = JSON.parse(cleaned);
    return Array.isArray(parsed.errors) ? parsed.errors : [];
  } catch (err) {
    throw new Error(`AI 응답을 JSON으로 파싱할 수 없습니다: ${err.message}\n${cleaned}`);
  }
};

const BATCH_SIZE = 50;

export const buildAiPrompt = (doc) => buildPromptPayload(doc);
export const runGeminiCheck = async (doc) => {
  const sentences = doc.sentences || [];
  if (sentences.length === 0) return [];

  const allErrors = [];
  const totalBatches = Math.ceil(sentences.length / BATCH_SIZE);

  for (let i = 0; i < sentences.length; i += BATCH_SIZE) {
    const batch = sentences.slice(i, i + BATCH_SIZE);
    const batchNum = Math.floor(i / BATCH_SIZE) + 1;
    console.log(`AI 검사 중: 배치 ${batchNum} / ${totalBatches} 처리 중...`);

    const partialDoc = { ...doc, sentences: batch };
    const { combined } = buildPromptPayload(partialDoc);

    const raw = await callGemini(combined);
    const errors = parseErrors(raw);
    allErrors.push(...errors);
  }

  return allErrors;
};
