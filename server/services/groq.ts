// server/services/groq.ts
import fetch from "node-fetch";

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
      model: params.model ?? "gpt-4o",
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
- X/Twitter (breaking news, expert opinions)
- Substack (in‑depth analysis, expert newsletters)
- Traditional Media (established news outlets)
- Specialized Publications (industry‑specific sources)

Return ONLY valid JSON in this format:
{"sources":[{"name":"","type":"","relevanceScore":0,"credibilityScore":0,"reasoning":""}]}`;

    try {
      const data: any = await callGroqChat({
        model: "gpt-4o",
        messages: [{ role: "user", content: prompt }],
      });

      const content = data?.choices?.[0]?.message?.content;
      if (!content) throw new Error("No content in Groq response.");
      const result = JSON.parse(content);
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
        model: "gpt-4o",
        messages: [{ role: "user", content: prompt }],
      });

      const content = data?.choices?.[0]?.message?.content;
      if (!content) throw new Error("No content in Groq response.");
      const result = JSON.parse(content);

      return articles.map((article, i) => {
        const a = result.rankedArticles.find((r: any) => r.originalIndex === i) || {};
        return {
          ...article,
          aiScore: a.aiScore ?? 50,
          topic: a.topicMatch ?? topics[0],
        };
      }).sort((a, b) => b.aiScore - a.aiScore);
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
        model: "gpt-4o",
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
