// server/services/groq.ts
import fetch from "node-fetch";

/*
 * JSON repair helper for Node.js.  We first attempt to load the
 * official ``jsonrepair`` package.  If it is available, we will use
 * its implementation, which handles a broad range of malformed JSON
 * scenarios.  If it is not available (for example, when running
 * locally without the dependency installed), we fall back to a
 * minimal implementation that repairs single quotes and trailing
 * commas.  Keeping the API consistent allows us to transparently use
 * either implementation.
 */
let jsonrepair: (text: string) => string;
try {
  // The npm package exports a function named ``jsonrepair``.  Some
  // versions also export a default function; we handle both cases.
  // eslint-disable-next-line @typescript-eslint/no-var-requires
  const lib = require('jsonrepair');
  jsonrepair = (lib.jsonrepair || lib) as (text: string) => string;
} catch (err) {
  console.warn('jsonrepair package not found, using fallback repair function');
  jsonrepair = function (text: string): string {
    if (typeof text !== 'string') return text as any;
    let repaired = text;
    // Replace single quotes with double quotes
    repaired = repaired.replace(/'/g, '"');
    // Remove trailing commas before closing braces or brackets
    repaired = repaired.replace(/,\s*([}\]])/g, '$1');
    return repaired;
  };
}

/**
 * Attempt to repair and parse a JSON-like string.  This helper wraps
 * ``jsonrepair`` and then calls ``JSON.parse`` on the result.  If
 * parsing fails, it logs the error and rethrows the exception.  By
 * centralizing the repair/parse logic here we avoid scattering
 * ad‑hoc JSON extraction throughout the service methods.
 */
function parseJsonContent(rawContent: string): any {
  try {
    let text = rawContent?.trim() ?? '';
    // Attempt to isolate the JSON portion.  Some LLM responses include
    // explanatory text before the JSON.  We look for the first '{' and
    // the last '}' and extract that substring.  If no braces are found
    // we fall back to the original text.
    const firstBrace = text.indexOf('{');
    const lastBrace = text.lastIndexOf('}');
    if (firstBrace !== -1 && lastBrace !== -1 && firstBrace < lastBrace) {
      text = text.slice(firstBrace, lastBrace + 1);
    }
    // Repair and parse the isolated JSON
    const repaired = jsonrepair(text);
    return JSON.parse(repaired);
  } catch (err) {
    console.error('Failed to parse JSON content:', err);
    throw err;
  }
}

const GROQ_API_KEY = process.env.GROQ_API_KEY!;
const GROQ_BASE_URL = "https://api.groq.com/openai/v1";

export interface NewsSource {
  name: string;
  type: string;
  relevanceScore: number;
  credibilityScore: number;
  reasoning: string;
}

export interface AnalyzedArticle {
  title: string;
  content: string;
  url: string;
  source: string;
  topic: string;
  aiScore: number;
  publishedAt: Date;
  metadata?: {
    views?: number;
    comments?: number;
    likes?: number;
    shares?: number;
    readTime?: string;
    author?: string;
  };
}

// Note: ``extractJsonFromText`` has been removed in favour of
// ``parseJsonContent``, which repairs and parses the entire content
// string directly.  This simplifies the parsing logic and avoids
// brittle regular expression matching.

async function callGroqChat(params: {
  model?: string;
  messages: { role: string; content: string }[];
}) {
  const resp = await fetch(`${GROQ_BASE_URL}/chat/completions`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${GROQ_API_KEY}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      model: params.model ?? "llama3-70b-8192",
      messages: params.messages,
    }),
  });

  if (!resp.ok) {
    const errorText = await resp.text();
    throw new Error(`Groq error ${resp.status}: ${errorText}`);
  }

  return resp.json();
}

export class GroqService {
  async selectNewsSources(topics: string[], region: string, excludedSources: string[] = []): Promise<NewsSource[]> {
    const prompt = `You are an AI news curation expert. Given the following topics and preferences, recommend the best news sources.

Topics: ${topics.join(', ')}
Region: ${region}
Excluded sources: ${excludedSources.join(', ') || 'None'}

Consider these source types:
- Reddit (community discussions, real-time reactions)
- Substack (in‑depth analysis, expert newsletters)
- Traditional Media (established news outlets)
- Specialized Publications (industry‑specific sources)

Return ONLY valid JSON in this format:
{"sources":[{"name":"","type":"","relevanceScore":0,"credibilityScore":0,"reasoning":""}]}`;

    try {
      const data: any = await callGroqChat({
        model: "llama3-70b-8192",
        messages: [{ role: "user", content: prompt }],
      });

      const content = data?.choices?.[0]?.message?.content;
      if (!content) throw new Error("No content in Groq response.");
      // Parse the returned content using our JSON repair helper
      const result = parseJsonContent(content);
      return result.sources || [];
    } catch (e) {
      console.error("selectNewsSources failed:", e);
      return this.getFallbackSources(topics);
    }
  }

  async analyzeAndRankArticles(articles: any[], topics: string[], userPreferences: any): Promise<AnalyzedArticle[]> {
    const prompt = `You are an AI news analyst. Analyze and rank these articles based on relevance, credibility, and user preferences.

User Topics: ${topics.join(', ')}
User Preferences: ${JSON.stringify(userPreferences)}
Articles to analyze: ${JSON.stringify(articles.slice(0, 20))}

For each article, return:
{"rankedArticles":[{"originalIndex":0,"aiScore":0,"reasoning":"","topicMatch":""}]}

Return ONLY valid JSON.`;

    try {
      const data: any = await callGroqChat({
        model: "llama3-70b-8192",
        messages: [{ role: "user", content: prompt }],
      });

      const content = data?.choices?.[0]?.message?.content;
      if (!content) throw new Error("No content in Groq response.");
      // Repair and parse the response as JSON
      const result = parseJsonContent(content);

      return articles
        .map((article, i) => {
          const a = (result?.rankedArticles || []).find(
            (r: any) => r.originalIndex === i
          ) || {};
          return {
            ...article,
            aiScore: a.aiScore ?? 50,
            topic: a.topicMatch ?? topics[0],
          };
        })
        .sort((a, b) => (b.aiScore || 0) - (a.aiScore || 0));
    } catch (e) {
      console.error("analyzeAndRankArticles failed:", e);
      return articles.map(article => ({
        ...article,
        aiScore: Math.floor(Math.random() * 40) + 60,
        topic: topics[0],
      }));
    }
  }

  async generateArticleSummary(content: string): Promise<string> {
    const prompt = `Summarize this news article in 2-3 sentences, maintaining key facts and context:\n\n${content.slice(0, 2000)}\n\nReturn only the summary.`;

    try {
      const data: any = await callGroqChat({
        model: "llama3-70b-8192",
        messages: [{ role: "user", content: prompt }],
      });

      return data?.choices?.[0]?.message?.content || content.slice(0, 200) + "...";
    } catch (e) {
      console.error("generateArticleSummary failed:", e);
      return content.slice(0, 200) + "...";
    }
  }

  private getFallbackSources(topics: string[]): NewsSource[] {
    return [
      {
        name: "Reuters",
        type: "News Agency",
        relevanceScore: 95,
        credibilityScore: 98,
        reasoning: "Exceptional credibility with comprehensive global coverage",
      },
      {
        name: "Associated Press",
        type: "News Agency",
        relevanceScore: 92,
        credibilityScore: 96,
        reasoning: "Reliable wire service with rigorous fact-checking standards",
      },
      {
        name: "BBC News",
        type: "Broadcaster",
        relevanceScore: 90,
        credibilityScore: 94,
        reasoning: "Global news coverage with strong editorial standards",
      },
      {
        name: "NPR",
        type: "Broadcaster",
        relevanceScore: 88,
        credibilityScore: 92,
        reasoning: "High-quality journalism with in-depth analysis",
      },
      {
        name: "The Guardian",
        type: "Newspaper",
        relevanceScore: 86,
        credibilityScore: 90,
        reasoning: "Strong digital presence with investigative journalism",
      },
      {
        name: "Substack",
        type: "Newsletter Platform",
        relevanceScore: 84,
        credibilityScore: 87,
        reasoning: "Independent journalists and expert analysis on specialized topics",
      },
      {
        name: "Reddit",
        type: "Social Media",
        relevanceScore: 82,
        credibilityScore: 75,
        reasoning: "Community discussions and early trend identification",
      },
    ];
  }
}

export const groqService = new GroqService();
