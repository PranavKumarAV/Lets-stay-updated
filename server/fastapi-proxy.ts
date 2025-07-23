/**
 * FastAPI Backend Proxy for Express Server
 * Forwards requests to the FastAPI backend or provides fallback responses
 */
import express from "express";
import fetch from "node-fetch";

const router = express.Router();
const FASTAPI_URL = process.env.FASTAPI_URL || "http://localhost:8000";

// Helper function to make requests to FastAPI backend
async function proxyToFastAPI(path: string, method: string = "GET", body?: any) {
  try {
    const response = await fetch(`${FASTAPI_URL}${path}`, {
      method,
      headers: {
        "Content-Type": "application/json",
        ...(body && { body: JSON.stringify(body) })
      },
      ...(body && { body: JSON.stringify(body) })
    });
    
    if (!response.ok) {
      throw new Error(`FastAPI error: ${response.status}`);
    }
    
    return await response.json();
  } catch (error) {
    console.error(`FastAPI proxy error for ${path}:`, error);
    throw error;
  }
}

// Mock news data for development/testing when FastAPI is unavailable
const getMockNewsData = (preferences: any) => {
  console.log("Using mock data for preferences:", preferences);
  const mockArticles = [
    {
      id: 1,
      title: "Breakthrough in AI Technology Transforms News Industry",
      content: "Recent advances in artificial intelligence are revolutionizing how news is curated and delivered to readers. AI-powered systems can now analyze thousands of articles in real-time, providing personalized news feeds that adapt to individual preferences and interests.",
      url: "https://example.com/ai-news-breakthrough",
      source: "TechNews Daily",
      topic: preferences.topics[0] || "AI Advancement",
      ai_score: 95,
      published_at: new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString(),
      fetched_at: new Date().toISOString(),
      metadata: { views: 15420, comments: 87 }
    },
    {
      id: 2,
      title: "Global Climate Summit Reaches Historic Agreement",
      content: "World leaders have reached a groundbreaking consensus on climate action at the international summit. The agreement includes specific targets for renewable energy adoption and carbon emission reductions across all participating nations.",
      url: "https://example.com/climate-summit-agreement",
      source: "Global News Network",
      topic: "Politics",
      ai_score: 88,
      published_at: new Date(Date.now() - 4 * 60 * 60 * 1000).toISOString(),
      fetched_at: new Date().toISOString(),
      metadata: { views: 23100, comments: 156 }
    },
    {
      id: 3,
      title: "Revolutionary Space Mission Launched Successfully",
      content: "A new era of space exploration begins as the latest mission launches with advanced technology that will enable deeper exploration of our solar system. The mission carries innovative instruments designed to search for signs of life on distant planets.",
      url: "https://example.com/space-mission-launch",
      source: "Space Today",
      topic: preferences.topics.includes("Science") ? "Science" : preferences.topics[0],
      ai_score: 92,
      published_at: new Date(Date.now() - 6 * 60 * 60 * 1000).toISOString(),
      fetched_at: new Date().toISOString(),
      metadata: { views: 18750, comments: 203 }
    }
  ];

  return {
    articles: mockArticles.slice(0, preferences.article_count || 10),
    total_count: mockArticles.length,
    generated_at: new Date().toISOString(),
    processing_time_ms: 1200
  };
};

// Generate news endpoint
router.post("/news/generate", async (req, res) => {
  try {
    // Log the incoming request for debugging
    console.log("Received news generation request:", req.body);
    
    const data = await proxyToFastAPI("/api/news/generate", "POST", req.body);
    res.json(data);
  } catch (error) {
    console.log("FastAPI unavailable, using mock data for development");
    
    // Ensure we have proper fallback data structure
    const mockResponse = getMockNewsData(req.body);
    res.json(mockResponse);
  }
});

// Get news sources endpoint
router.post("/news/sources", async (req, res) => {
  try {
    const data = await proxyToFastAPI("/api/news/sources", "POST", req.body);
    res.json(data);
  } catch (error) {
    console.log("FastAPI unavailable, using mock sources");
    res.json({
      sources: [
        {
          name: "Reuters",
          type: "news_agency",
          relevanceScore: 95,
          credibilityScore: 98,
          reasoning: "Global news agency with exceptional credibility"
        },
        {
          name: "BBC News",
          type: "broadcaster", 
          relevanceScore: 90,
          credibilityScore: 94,
          reasoning: "Trusted international broadcaster"
        }
      ]
    });
  }
});

// Health check endpoint
router.get("/health", async (req, res) => {
  try {
    const data = await proxyToFastAPI("/api/health");
    res.json(data);
  } catch (error) {
    res.json({
      status: "ok",
      message: "Express proxy server is healthy (FastAPI backend unavailable)",
      timestamp: new Date().toISOString(),
      groq_available: false
    });
  }
});

// Get cached articles endpoint
router.get("/news/articles", async (req, res) => {
  try {
    const queryString = new URLSearchParams(req.query as any).toString();
    const data = await proxyToFastAPI(`/api/news/articles?${queryString}`);
    res.json(data);
  } catch (error) {
    res.json({ articles: [], count: 0 });
  }
});

export default router;