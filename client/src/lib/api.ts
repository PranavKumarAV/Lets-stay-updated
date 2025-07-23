import { apiRequest } from "./queryClient";

export interface NewsArticle {
  id: number;
  title: string;
  content: string;
  url: string;
  source: string;
  topic: string;
  ai_score: number;
  published_at: string;
  fetched_at: string;
  metadata?: Record<string, any>;
}

export interface NewsSource {
  name: string;
  type: string;
  relevanceScore: number;
  credibilityScore: number;
  reasoning: string;
}

export interface GenerateNewsRequest {
  region: string;
  country?: string;
  topics: string[];
  article_count: number;
  excluded_sources?: string[];
}

export interface GenerateNewsResponse {
  articles: NewsArticle[];
  total_count: number;
  generated_at: string;
  processing_time_ms?: number;
}

export interface GetSourcesResponse {
  sources: NewsSource[];
}

export interface HealthResponse {
  status: string;
  message: string;
  timestamp?: string;
  groq_available: boolean;
}

// API base URL - adjust for FastAPI backend
const API_BASE = "/api";

export const newsApi = {
  async generateNews(request: GenerateNewsRequest): Promise<GenerateNewsResponse> {
    const response = await apiRequest("POST", `${API_BASE}/news/generate`, request);
    return response.json();
  },

  async getSources(topics: string[], region: string, excludedSources: string[] = []): Promise<GetSourcesResponse> {
    const response = await apiRequest("POST", `${API_BASE}/news/sources`, {
      topics,
      region,
      excluded_sources: excludedSources
    });
    return response.json();
  },

  async getCachedArticles(params: {
    topics?: string[];
    source?: string;
    min_ai_score?: number;
    limit?: number;
  } = {}): Promise<{ articles: NewsArticle[]; count: number }> {
    const searchParams = new URLSearchParams();
    
    if (params.topics?.length) {
      searchParams.append("topics", params.topics.join(","));
    }
    if (params.source) {
      searchParams.append("source", params.source);
    }
    if (params.min_ai_score) {
      searchParams.append("min_ai_score", params.min_ai_score.toString());
    }
    if (params.limit) {
      searchParams.append("limit", params.limit.toString());
    }

    const url = `${API_BASE}/news/articles${searchParams.toString() ? `?${searchParams}` : ""}`;
    const response = await apiRequest("GET", url);
    return response.json();
  },

  async checkHealth(): Promise<HealthResponse> {
    const response = await apiRequest("GET", `${API_BASE}/health`);
    return response.json();
  },

  async cleanup(): Promise<{ message: string }> {
    const response = await apiRequest("POST", `${API_BASE}/news/cleanup`);
    return response.json();
  }
};