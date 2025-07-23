import { newsPreferences, newsArticles, type NewsPreferences, type InsertNewsPreferences, type NewsArticle, type InsertNewsArticle } from "@shared/schema";

export interface IStorage {
  // News preferences
  createNewsPreferences(preferences: InsertNewsPreferences): Promise<NewsPreferences>;
  getNewsPreferences(id: number): Promise<NewsPreferences | undefined>;
  
  // News articles
  createNewsArticle(article: InsertNewsArticle): Promise<NewsArticle>;
  getNewsArticles(filters: {
    topics?: string[];
    source?: string;
    minAiScore?: number;
    limit?: number;
  }): Promise<NewsArticle[]>;
  clearOldArticles(): Promise<void>;
}

export class MemStorage implements IStorage {
  private preferences: Map<number, NewsPreferences>;
  private articles: Map<number, NewsArticle>;
  private currentPreferencesId: number;
  private currentArticleId: number;

  constructor() {
    this.preferences = new Map();
    this.articles = new Map();
    this.currentPreferencesId = 1;
    this.currentArticleId = 1;
  }

  async createNewsPreferences(insertPreferences: InsertNewsPreferences): Promise<NewsPreferences> {
    const id = this.currentPreferencesId++;
    const preferences: NewsPreferences = {
      ...insertPreferences,
      id,
      country: insertPreferences.country || null,
      createdAt: new Date(),
    };
    this.preferences.set(id, preferences);
    return preferences;
  }

  async getNewsPreferences(id: number): Promise<NewsPreferences | undefined> {
    return this.preferences.get(id);
  }

  async createNewsArticle(insertArticle: InsertNewsArticle): Promise<NewsArticle> {
    const id = this.currentArticleId++;
    const article: NewsArticle = {
      ...insertArticle,
      id,
      fetchedAt: new Date(),
    };
    this.articles.set(id, article);
    return article;
  }

  async getNewsArticles(filters: {
    topics?: string[];
    source?: string;
    minAiScore?: number;
    limit?: number;
  }): Promise<NewsArticle[]> {
    let articles = Array.from(this.articles.values());

    if (filters.topics && filters.topics.length > 0) {
      articles = articles.filter(article => filters.topics!.includes(article.topic));
    }

    if (filters.source) {
      articles = articles.filter(article => article.source === filters.source);
    }

    if (filters.minAiScore) {
      articles = articles.filter(article => article.aiScore >= filters.minAiScore!);
    }

    // Sort by AI score (highest first) and then by published date
    articles.sort((a, b) => {
      if (b.aiScore !== a.aiScore) {
        return b.aiScore - a.aiScore;
      }
      return new Date(b.publishedAt).getTime() - new Date(a.publishedAt).getTime();
    });

    if (filters.limit) {
      articles = articles.slice(0, filters.limit);
    }

    return articles;
  }

  async clearOldArticles(): Promise<void> {
    const oneDayAgo = new Date(Date.now() - 24 * 60 * 60 * 1000);
    const articlesToKeep = Array.from(this.articles.values()).filter(
      article => new Date(article.fetchedAt) > oneDayAgo
    );
    
    this.articles.clear();
    articlesToKeep.forEach(article => this.articles.set(article.id, article));
  }
}

export const storage = new MemStorage();
