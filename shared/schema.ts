import { pgTable, text, serial, integer, boolean, timestamp, jsonb } from "drizzle-orm/pg-core";
import { createInsertSchema } from "drizzle-zod";
import { z } from "zod";

export const newsPreferences = pgTable("news_preferences", {
  id: serial("id").primaryKey(),
  region: text("region").notNull(), // "international" or country code
  country: text("country"), // specific country if region is "country"
  topics: jsonb("topics").notNull(), // array of selected topics
  articleCount: integer("article_count").notNull().default(10),
  excludedSources: jsonb("excluded_sources"), // array of excluded source names
  createdAt: timestamp("created_at").defaultNow().notNull(),
});

export const newsArticles = pgTable("news_articles", {
  id: serial("id").primaryKey(),
  title: text("title").notNull(),
  content: text("content").notNull(),
  url: text("url").notNull(),
  source: text("source").notNull(),
  topic: text("topic").notNull(),
  aiScore: integer("ai_score").notNull(), // 0-100 relevance score
  publishedAt: timestamp("published_at").notNull(),
  fetchedAt: timestamp("fetched_at").defaultNow().notNull(),
});

export const insertNewsPreferencesSchema = createInsertSchema(newsPreferences).omit({
  id: true,
  createdAt: true,
});

export const insertNewsArticleSchema = createInsertSchema(newsArticles).omit({
  id: true,
  fetchedAt: true,
});

export type InsertNewsPreferences = z.infer<typeof insertNewsPreferencesSchema>;
export type NewsPreferences = typeof newsPreferences.$inferSelect;
export type InsertNewsArticle = z.infer<typeof insertNewsArticleSchema>;
export type NewsArticle = typeof newsArticles.$inferSelect;

// Request/Response schemas for API
export const generateNewsRequestSchema = z.object({
  region: z.string(),
  country: z.string().optional(),
  topics: z.array(z.string()).min(1),
  articleCount: z.number().min(5).max(50),
  excludedSources: z.array(z.string()).optional(),
});

export type GenerateNewsRequest = z.infer<typeof generateNewsRequestSchema>;

export const newsResponseSchema = z.object({
  articles: z.array(z.object({
    id: z.number(),
    title: z.string(),
    content: z.string(),
    url: z.string(),
    source: z.string(),
    topic: z.string(),
    aiScore: z.number(),
    publishedAt: z.string(),
    metadata: z.object({
      views: z.number().optional(),
      comments: z.number().optional(),
      likes: z.number().optional(),
      shares: z.number().optional(),
      readTime: z.string().optional(),
      author: z.string().optional(),
    }).optional(),
  })),
  totalCount: z.number(),
  generatedAt: z.string(),
});

export type NewsResponse = z.infer<typeof newsResponseSchema>;
