import type { Express } from "express";
import { createServer, type Server } from "http";
import { storage } from "./storage";
import { groqService } from "./services/groq"; 
import { generateNewsRequestSchema, type GenerateNewsRequest, type NewsResponse } from "@shared/schema";
import { z } from "zod";

export async function registerRoutes(app: Express): Promise<Server> {
  app.post("/api/news/generate", async (req, res) => {
    try {
      const requestBody = {
        ...req.body,
        articleCount: req.body.articleCount || req.body.article_count || 10
      };
      console.log("Processing request:", requestBody);

      const validatedData = generateNewsRequestSchema.parse(requestBody);
      const { region, country, topics, articleCount, excludedSources = [] } = validatedData;

      // Step 1: Groq selects best news sources
      const selectedSources = await groqService.selectNewsSources(topics, region, excludedSources);
      console.log('Groq selected sources:', selectedSources.map(s => s.name));

      // Step 2: Simulate fetching articles from selected sources
      const mockArticles = await simulateFetchingArticles(topics, selectedSources, articleCount);

      // Step 3: Groq analyzes and ranks articles
      const rankedArticles = await groqService.analyzeAndRankArticles(
        mockArticles,
        topics,
        { region, country, excludedSources }
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
      const { topics, region, excludedSources } = req.body;
      const sources = await groqService.selectNewsSources(topics, region, excludedSources);
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
      if (topics) filters.topics = (topics as string).split(',');
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
