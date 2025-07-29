import type { Express } from "express";
import { createServer, type Server } from "http";
import { storage } from "./storage";
import { groqService } from "./services/groq"; 
import { generateNewsRequestSchema, type GenerateNewsRequest, type NewsResponse } from "@shared/schema";
import { z } from "zod";
import Parser from "rss-parser";
import fetch from "node-fetch";

export async function registerRoutes(app: Express): Promise<Server> {
  app.post("/api/news/generate", async (req, res) => {
    try {
      const requestBody = {
        ...req.body,
        articleCount: req.body.articleCount || req.body.article_count || 10
      };
      console.log("Processing request:", requestBody);

      const validatedData = generateNewsRequestSchema.parse(requestBody);
      const { region, country, topics, articleCount} = validatedData;

      // Step 1: Groq selects best news sources
      const selectedSources = await groqService.selectNewsSources(topics, region);
      console.log('Groq selected sources:', selectedSources.map(s => s.name));

      // Step 2: Attempt to fetch real articles via NewsAPI or RSS feeds.
      // If this returns an empty array, fall back to mock generation.
      let articlesToAnalyze: any[] = [];
      try {
        articlesToAnalyze = await fetchArticlesReal(topics, selectedSources, articleCount);
      } catch (err) {
        console.error('Error fetching real articles, falling back to mock:', err);
      }
      if (!articlesToAnalyze || articlesToAnalyze.length === 0) {
        articlesToAnalyze = await simulateFetchingArticles(topics, selectedSources, articleCount);
      }

      // Step 3: Groq analyzes and ranks articles
      const rankedArticles = await groqService.analyzeAndRankArticles(
        articlesToAnalyze,
        topics,
        { region, country}
      );

      // Step 4: Store articles and return response
      const storedArticles = [];
      for (const article of rankedArticles.slice(0, articleCount)) {
        const stored = await storage.createNewsArticle({
          title: article.title,
          content: article.content,
          url: article.url,
          source: article.source,
          topic: article.topic,
          aiScore: article.aiScore,
          publishedAt: article.publishedAt,
        });
        storedArticles.push({
          ...stored,
          publishedAt: stored.publishedAt.toISOString(),
          metadata: article.metadata,
        });
      }

      const response: NewsResponse = {
        articles: storedArticles,
        totalCount: storedArticles.length,
        generatedAt: new Date().toISOString(),
      };

      res.json(response);
    } catch (error) {
      console.error('Error generating news:', error);
      if (error instanceof z.ZodError) {
        res.status(400).json({ message: "Invalid request data", errors: error.errors });
      } else {
        res.status(500).json({ message: "Failed to generate news feed" });
      }
    }
  });

  app.post("/api/news/sources", async (req, res) => {
    try {
      const { topics, region} = req.body;
      const sources = await groqService.selectNewsSources(topics, region);
      res.json({ sources });
    } catch (error) {
      console.error('Error getting sources:', error);
      res.status(500).json({ message: "Failed to get news sources" });
    }
  });

  app.get("/api/news/articles", async (req, res) => {
    try {
      const { topics, source, minAiScore, limit } = req.query;

      const filters: any = {};
      if (topics && Array.isArray(topics)) filters.topics = topics;
      if (source) filters.source = source;
      if (minAiScore) filters.minAiScore = parseInt(minAiScore as string);
      if (limit) filters.limit = parseInt(limit as string);

      const articles = await storage.getNewsArticles(filters);
      res.json({ articles });
    } catch (error) {
      console.error('Error getting articles:', error);
      res.status(500).json({ message: "Failed to get articles" });
    }
  });

  app.post("/api/news/cleanup", async (req, res) => {
    try {
      await storage.clearOldArticles();
      res.json({ message: "Old articles cleared successfully" });
    } catch (error) {
      console.error('Error cleaning up articles:', error);
      res.status(500).json({ message: "Failed to clean up articles" });
    }
  });

  const httpServer = createServer(app);
  return httpServer;
}

// Simulate fetching articles from various sources (X/Twitter removed due to API restrictions)
async function simulateFetchingArticles(topics: string[], sources: any[], count: number) {
  const articles = [];
  // Filter out X/Twitter sources for reliability
  const validSources = sources.filter(s => 
    !s.name.toLowerCase().includes('twitter') && 
    !s.name.toLowerCase().includes('x (') &&
    s.name !== 'X'
  );
  const sourceNames = validSources.map(s => s.name);
  
  // Generate realistic article data for each topic and source combination
  for (const topic of topics) {
    for (const sourceName of sourceNames) {
      const articlesPerSource = Math.ceil(count / (topics.length * sourceNames.length)) + 2;
      
      for (let i = 0; i < articlesPerSource; i++) {
        articles.push({
          title: generateArticleTitle(topic, sourceName),
          content: generateArticleContent(topic),
          url: `https://example.com/${topic.toLowerCase().replace(' ', '-')}-${i}`,
          source: sourceName,
          publishedAt: new Date(Date.now() - Math.random() * 24 * 60 * 60 * 1000), // Last 24 hours
          metadata: generateMetadata(sourceName),
        });
      }
    }
  }

  // Return more articles than requested so AI can select the best ones
  return articles.slice(0, count * 2);
}

function generateArticleTitle(topic: string, source: string): string {
  const templates = {
    "politics": [
      "Breaking: Major Policy Changes Announced in {topic}",
      "Senate Votes on Landmark {topic} Legislation",
      "Political Analysis: {topic} Impact on Upcoming Elections",
      "International Relations: {topic} Diplomatic Breakthrough",
      "Expert Opinion: {topic} Policy Implications"
    ],
    "sports": [
      "Championship Update: {topic} Tournament Results",
      "Player Transfer News Shakes {topic} World",
      "Record-Breaking Performance in {topic} Competition",
      "Injury Report: Key {topic} Players Sidelined",
      "Season Analysis: {topic} Team Standings"
    ],
    "ai": [
      "AI Breakthrough: Revolutionary {topic} Technology",
      "Tech Giants Invest Billions in {topic} Research",
      "Ethical Concerns Raised Over {topic} Development",
      "Industry Impact: {topic} Transforms Business Operations",
      "Research Paper: {topic} Advances Published"
    ],
    "movies": [
      "Box Office Hit: {topic} Film Breaks Records",
      "Celebrity News: {topic} Stars Announce New Project",
      "Film Festival: {topic} Movies Win Critical Acclaim",
      "Industry Insider: {topic} Production Updates",
      "Review: {topic} Film Receives Mixed Reception"
    ]
  };

  const topicKey = topic.toLowerCase().includes('ai') ? 'ai' : 
                   topic.toLowerCase().includes('politics') ? 'politics' :
                   topic.toLowerCase().includes('sports') ? 'sports' :
                   topic.toLowerCase().includes('movie') ? 'movies' : 'politics';

  const topicTemplates = templates[topicKey] || templates.politics;
  const template = topicTemplates[Math.floor(Math.random() * topicTemplates.length)];
  
  return template.replace('{topic}', topic);
}

function generateArticleContent(topic: string): string {
  const baseContent = `This is a comprehensive article about ${topic}. The recent developments in this field have been significant, with multiple stakeholders weighing in on the implications. Industry experts suggest that these changes will have far-reaching consequences for the sector. The analysis reveals both opportunities and challenges ahead. Key findings indicate a shift in the traditional approach, with new methodologies being adopted across the board. Stakeholders are closely monitoring the situation as it continues to evolve. The impact on related sectors is expected to be substantial, requiring careful consideration of next steps.`;
  
  return baseContent + ` Additional context about ${topic} reveals deeper insights into the underlying trends and patterns that are shaping this space.`;
}

function generateMetadata(source: string) {
  if (source.toLowerCase().includes('reddit')) {
    return {
      views: Math.floor(Math.random() * 50000) + 1000,
      comments: Math.floor(Math.random() * 1000) + 50,
    };
  } else if (source.toLowerCase().includes('guardian')) {
    return {
      views: Math.floor(Math.random() * 75000) + 5000,
      shares: Math.floor(Math.random() * 3000) + 200,
      readTime: `${Math.floor(Math.random() * 8) + 3} min read`,
    };
  } else if (source.toLowerCase().includes('substack')) {
    return {
      author: `${['Sarah Chen', 'David Rodriguez', 'Emily Watson', 'Michael Thompson'][Math.floor(Math.random() * 4)]}`,
      readTime: `${Math.floor(Math.random() * 10) + 3} min read`,
    };
  } else {
    return {
      views: Math.floor(Math.random() * 25000) + 500,
    };
  }
}

/**
 * Fetch real news articles using either the NewsAPI.org service or RSS feeds.
 * If the environment variable `NEWS_API_KEY` is defined, the function will
 * prefer NewsAPI for supported sources; otherwise it will fall back to RSS.
 * When neither real data source yields results, it will return an empty array
 * so the caller can choose to generate mock articles.
 *
 * @param topics List of user topics
 * @param selectedSources List of selected source objects from Groq
 * @param count Number of articles requested by the user
 */
async function fetchArticlesReal(
  topics: string[],
  selectedSources: any[],
  count: number,
): Promise<any[]> {
  const apiKey = process.env.NEWS_API_KEY;
  const articles: any[] = [];
  const parser = new Parser();
  const maxPerSource = Math.max(
    1,
    Math.ceil(count / Math.max(1, topics.length * selectedSources.length)),
  );
  // Normalize topics for simple keyword matching
  const topicKeywords = topics.map(t => t.toLowerCase() === 'ai' ? 'artificial intelligence' : t.toLowerCase());

  for (const topic of topics) {
    for (const src of selectedSources) {
      const name = src.name;
      // Prefer NewsAPI if an API key is provided and this source has a newsapiId
      if (apiKey && src.newsapiId) {
        try {
          const sourceId = src.newsapiId;
          const url =
            `https://newsapi.org/v2/everything` +
            `?q=${encodeURIComponent(topic)}` +
            `&sources=${encodeURIComponent(sourceId)}` +
            `&pageSize=${maxPerSource}` +
            `&sortBy=publishedAt&apiKey=${apiKey}`;
          const resp = await fetch(url);
          if (resp.ok) {
            const data = (await resp.json()) as any;
            for (const item of data.articles || []) {
              const summary = (item.description || item.content || '').slice(0, 200);
              articles.push({
                title: item.title || '',
                content: summary,
                url: item.url || '',
                source: name,
                publishedAt: item.publishedAt ? new Date(item.publishedAt) : new Date(),
                metadata: {
                  author: item.author,
                  source_name: item.source?.name,
                },
              });
            }
            continue; // Skip RSS if NewsAPI succeeded for this source
          } else {
            console.warn(`NewsAPI responded with status ${resp.status} for ${name}`);
          }
        } catch (err) {
          console.error(`Error fetching NewsAPI for ${name}:`, err);
        }
      }
      // If no API key or no newsapiId, try RSS using the feedUrl provided by the LLM
      const feedUrl = src.feedUrl;
      if (!feedUrl) continue;
      try {
        const feed = await parser.parseURL(feedUrl);
        for (const entry of feed.items.slice(0, maxPerSource * 2)) {
          const title = entry.title || '';
          const description = entry.contentSnippet || entry.content || '';
          const combinedText = `${title} ${description}`.toLowerCase();
          if (!topicKeywords.some((kw) => kw.split(' ').every(word => combinedText.includes(word)))) {
            continue;
          }
          articles.push({
            title,
            content: description.slice(0, 200),
            url: entry.link || '',
            source: name,
            publishedAt: entry.isoDate ? new Date(entry.isoDate) : new Date(),
            metadata: {
              rss: true,
            },
          });
        }
      } catch (err) {
        console.error(`Error parsing RSS for ${name}:`, err);
      }
    }
  }
  // Sort by published date descending
  articles.sort((a, b) => (b.publishedAt as any) - (a.publishedAt as any));
  // Return more articles than requested so the AI can filter
  return articles.slice(0, count * 2);
}
