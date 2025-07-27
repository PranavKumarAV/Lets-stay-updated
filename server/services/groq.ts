// server/services/groq.ts
import fetch from "node-fetch";
import { jsonrepair } from "jsonrepair";

// Reliable fallback sources (used if LLM fails)
export const AVAILABLE_SOURCES = [
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

function parseJsonContent(rawContent: string): any {
  try {
    let text = rawContent?.trim() ?? "";
    const firstBrace = text.indexOf("{");
    const lastBrace = text.lastIndexOf("}");
    if (firstBrace !== -1 && lastBrace !== -1 && firstBrace < lastBrace) {
      text = text.slice(firstBrace, lastBrace + 1);
    }
    const repaired = jsonrepair(text);
    return JSON.parse(repaired);
  } catch (err) {
    console.error("Failed to parse JSON content:", err);
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
  async selectNewsSources(
    topics: string[],
    region: string,
    excludedSources: string[] = []
  ): Promise<any[]> {
    const prompt = `You are an AI news curation expert. Given the following topics and region, recommend the best 3 news providers. If the region is 'country', select outlets that primarily serve that country. If the region is 'international', choose globally recognized news providers. Return only sources with a valid RSS feed (feedUrl) or public API ID (newsapiId). Avoid social media platforms like Reddit, Substack, or Twitter. Respond ONLY with JSON in this format: [{"name": "Provider Name", "feedUrl": "https://...", "newsapiId": "id-if-available"}].`;

    try {
      const data: any = await callGroqChat({
        model: "llama3-70b-8192",
        messages: [{ role: "user", content: prompt }],
      });

      const content = data?.choices?.[0]?.message?.content;
      if (!content) throw new Error("No content in Groq response.");
      const result = parseJsonContent(content);
      return result.sources || result || [];
    } catch (e) {
      console.error("selectNewsSources failed:", e);
      return AVAILABLE_SOURCES.filter(
        (src) => !excludedSources.includes(src.name)
      ).map((src) => ({
        name: src.name,
        type: src.type,
        feedUrl: src.feedUrl || "",
        newsapiId: src.newsapiId || "",
        reasoning: "default fallback source",
      }));
    }
  }

  async analyzeAndRankArticles(
    articles: any[],
    topics: string[],
    userPreferences: any
  ): Promise<AnalyzedArticle[]> {
    const prompt = `You are an AI news analyst. Analyze and rank these articles based on relevance, credibility, and user preferences.

User Topics: ${topics.join(", ")}
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
      const result = parseJsonContent(content);

      return articles
        .map((article, i) => {
          const a =
            (result?.rankedArticles || []).find(
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
      return articles.map((article) => ({
        ...article,
        aiScore: Math.floor(Math.random() * 40) + 60,
        topic: topics[0],
      }));
    }
  }

  async generateArticleSummary(content: string): Promise<string> {
    const prompt = `Summarize this news article in 2-3 sentences, maintaining key facts and context:\n\n${content.slice(
      0,
      2000
    )}\n\nReturn only the summary.`;

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
}

export const groqService = new GroqService();
