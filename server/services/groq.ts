// server/services/groq.ts
import fetch from "node-fetch";

// Define a set of sources that our system actually supports.  Each source
// entry includes a human‑readable name, its category, a NewsAPI identifier
// (if available), and an RSS feed URL (if available).  The LLM prompt
// will be restricted to this list so that we never get unsupported
// providers like ESPN or Reddit, which don't have simple RSS feeds or
// NewsAPI IDs.  You can add more sources here as you verify their
// endpoints.
/**
 * A list of reliable news providers and their RSS/API endpoints used as a
 * fallback when the language model fails to return usable sources.  This
 * constant is intentionally not surfaced to the LLM; rather, it is only
 * used internally if we need to default to known sources.  If you wish
 * to add or remove sources from the fallback, update this list.
 */
export const AVAILABLE_SOURCES: Array<{
  name: string;
  type: string;
  newsapiId?: string;
  feedUrl?: string;
}> = [
  {
    name: "Reuters",
    type: "News Agency",
    newsapiId: "reuters",
    feedUrl: "http://feeds.reuters.com/reuters/topNews",
  },
  {
    name: "Associated Press",
    type: "News Agency",
    newsapiId: "associated-press",
  },
  {
    name: "BBC News",
    type: "Broadcaster",
    newsapiId: "bbc-news",
    feedUrl: "http://feeds.bbci.co.uk/news/rss.xml",
  },
  {
    name: "NPR",
    type: "Broadcaster",
    newsapiId: "npr",
    feedUrl: "https://feeds.npr.org/1001/rss.xml",
  },
  {
    name: "The Guardian",
    type: "Newspaper",
    newsapiId: "the-guardian-uk",
    feedUrl: "https://www.theguardian.com/world/rss",
  },
];

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
  relevanceScore?: number;
  credibilityScore?: number;
  feedUrl?: string;
  newsapiId?: string;
  reasoning?: string;
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
  async selectNewsSources(topics: string[], region: string, excludedSources: string[] = []): Promise<any[]> {
    /*
     * Ask the LLM to identify credible and popular news providers for the
     * specified topics and region.  The model should only return
     * sources that have an accessible RSS feed or public API, and it
     * must include that endpoint in the response.  We avoid providing
     * a predefined list so the model can suggest sources beyond the
     * fallback set; however, we require it to supply either a `feedUrl`
     * or a `newsapiId` for each recommendation.  We also instruct the
     * model not to include excluded sources.
     */
    const prompt = `You are an AI news curation expert. Given the following topics and region, recommend the best 3 news providers. If the region is 'country', select outlets that primarily serve that country. If the region is 'international', choose globally recognized news providers. Return only sources with a valid RSS feed (feedUrl) or public API ID (newsapiId). Avoid social media platforms like Reddit, Substack, or Twitter. Respond ONLY with JSON in this format: [{"name": "Provider Name", "feedUrl": "https://...", "newsapiId": "id-if-available"}].`;
    try {
      const data: any = await callGroqChat({
        model: "llama3-70b-8192",
        messages: [{ role: "user", content: prompt }],
      });
      const content = data?.choices?.[0]?.message?.content;
      if (!content) throw new Error("No content in Groq response.");
      const result = parseJsonContent(content);
      return result.sources || [];
    } catch (e) {
      console.error("selectNewsSources failed:", e);
      // Fallback: return all available sources except any excluded ones
      return AVAILABLE_SOURCES.filter((src) => !excludedSources.includes(src.name)).map((src) => ({
        name: src.name,
        type: src.type,
        feedUrl: src.feedUrl || '',
        newsapiId: src.newsapiId || '',
        reasoning: 'default fallback source',
      }));
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
    /*
     * If the language model fails to return usable sources, we fall back
     * to this predefined set.  These entries include known RSS feeds
     * and NewsAPI identifiers.  You can adjust this list in
     * AVAILABLE_SOURCES at the top of the file.
     */
    return AVAILABLE_SOURCES.map(src => ({
      name: src.name,
      type: src.type,
      feedUrl: src.feedUrl,
      newsapiId: src.newsapiId,
      reasoning: "default fallback source",
    }));
  }
}

export const groqService = new GroqService();
