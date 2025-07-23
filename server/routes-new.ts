import type { Express } from "express";
import { db } from "./storage";
import fastApiProxy from "./fastapi-proxy";

export function registerRoutes(app: Express) {
  // Mount FastAPI proxy routes
  app.use("/api", fastApiProxy);
  
  // Health check endpoint
  app.get("/health", (req, res) => {
    res.json({ 
      status: "ok", 
      message: "Express server is healthy",
      timestamp: new Date().toISOString()
    });
  });
}