# AI-Powered News Aggregator

An intelligent news curation website that uses AI to select sources and rank articles based on relevance and popularity.

## Features

- **AI-Powered Source Selection**: Automatically selects the best news sources for your topics
- **Smart Article Ranking**: Uses AI to rank articles by relevance and quality
- **Multi-Step Configuration**: Easy-to-use wizard for selecting region, topics, and preferences
- **Real-time Updates**: Get fresh news curated specifically for your interests
- **Responsive Design**: Works perfectly on desktop and mobile devices

## Tech Stack

- **Frontend**: React 18 + TypeScript + Vite
- **Backend**: Express.js + TypeScript
- **Database**: PostgreSQL with Drizzle ORM
- **AI**: OpenAI GPT-4o or Groq Llama (free option)
- **UI**: Tailwind CSS + Radix UI components
- **State Management**: TanStack React Query

## Quick Start

### 1. Clone and Install

```bash
git clone <your-repo-url>
cd news-aggregator
npm install
```

### 2. Environment Setup

Copy `.env.example` to `.env` and configure:

**Option A: Using Groq (Free)**
```env
DATABASE_URL=postgresql://username:password@hostname:port/database
GROQ_API_KEY=gsk_your-groq-api-key-here
LLM_PROVIDER=groq
NODE_ENV=production
PORT=5000
```

**Option B: Using OpenAI (Paid, ~$2-10/month)**
```env
DATABASE_URL=postgresql://username:password@hostname:port/database
OPENAI_API_KEY=sk-your-openai-api-key-here
LLM_PROVIDER=openai
NODE_ENV=production
PORT=5000
```

### 3. Build and Run

```bash
# Build the application
npm run build

# Start the server
npm start
```

## Development

```bash
# Start development server
npm run dev
```

## API Keys

### Free Option: Groq API
- Get free API key from [Groq Console](https://console.groq.com)
- Fast responses, good quality
- Rate limits on free tier

### Paid Option: OpenAI API  
- Get API key from [OpenAI Platform](https://platform.openai.com/api-keys)
- Highest quality results (~$2-10/month)
- No rate limits

## Deployment

This application is optimized for deployment on:

- Render.com (recommended)
- Vercel
- Railway
- Any Node.js hosting service

See DEPLOYMENT.md for detailed setup guides.

## License

MIT License - feel free to use for personal and commercial projects.