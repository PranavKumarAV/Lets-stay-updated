# Let's Stay Updated - AI-Powered News Curation

An intelligent news aggregation platform that uses AI to select, analyze, and rank news articles from various sources based on your preferences. Built with modern technologies and **FREE AI models** for cost-effective deployment.

## Features

- **AI-Powered Source Selection**: Intelligent selection of news sources using **Groq's FREE API**
- **Smart Article Ranking**: AI analyzes and ranks articles by relevance, credibility, and quality
- **Multi-Step Configuration**: Easy-to-use wizard for setting up your preferences
- **Flexible Topic Selection**: Choose from popular categories or create custom topics
- **Source Exclusion**: Option to exclude specific news sources you don't want
- **Real-time Curation**: Get fresh, AI-curated news feeds on demand
- **Cost-Effective**: Uses FREE Groq API with generous limits (30 req/min, 1M tokens/hour)

## Technology Stack

### Frontend
- **React 18** with TypeScript
- **Wouter** for routing
- **TanStack React Query** for state management
- **Radix UI** + **shadcn/ui** for components
- **Tailwind CSS** for styling
- **Vite** for build tooling

### Backend
- **FastAPI** with Python 3.11+ (ultra-fast async API)
- **Groq API** for FREE AI processing (Llama 3 70B model)
- **SQLite** for lightweight database (PostgreSQL supported)
- **Pydantic** for data validation

## Environment Variables

Create a `.env` file with the following variables:

```env
# Required: Groq API Key for FREE AI features
GROQ_API_KEY=your_groq_api_key_here

# Optional: Database connection (uses SQLite if not provided)
DATABASE_URL=sqlite:///./news_app.db

# Optional: Application port (defaults to 5000)
PORT=5000

# Environment
ENVIRONMENT=production
```

### Getting Your FREE Groq API Key:
1. Go to https://console.groq.com/
2. Sign up for a free account
3. Create an API key in the console
4. Get 30 requests/minute and 1M tokens/hour for FREE!

## Installation and Setup

1. **Clone the repository**
   ```bash
   git clone <your-repo-url>
   cd news-curation-app
   ```

2. **Install dependencies**
   ```bash
   npm install
   ```

3. **Set up environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your API keys
   ```

4. **Build the application**
   ```bash
   npm run build
   ```

5. **Start the production server**
   ```bash
   npm start
   ```

For development:
```bash
npm run dev
```

## Deployment on Render.com

### Option 1: Using render.yaml (Recommended)

1. **Connect your repository** to Render.com
2. **Add environment variables** in the Render dashboard:
   - `OPENAI_API_KEY`: Your OpenAI API key
   - `NODE_ENV`: `production`
3. **Deploy** - Render will automatically use the `render.yaml` configuration

### Option 2: Manual Setup

1. **Create a new Web Service** on Render.com
2. **Connect your GitHub repository**
3. **Configure the service**:
   - **Build Command**: `npm install && npm run build`
   - **Start Command**: `npm start`
   - **Node Version**: 20
   - **Health Check Path**: `/health`
4. **Add environment variables**:
   - `OPENAI_API_KEY`
   - `NODE_ENV=production`
5. **Deploy**

### Option 3: Docker Deployment

Use the included `Dockerfile`:

```bash
# Build the image
docker build -t news-curation-app .

# Run the container
docker run -p 5000:5000 \
  -e OPENAI_API_KEY=your_key_here \
  -e NODE_ENV=production \
  news-curation-app
```

## API Endpoints

- `GET /health` - Health check endpoint
- `POST /api/news/generate` - Generate curated news feed
- `POST /api/news/sources` - Get recommended news sources
- `GET /api/news/articles` - Get cached articles
- `POST /api/news/cleanup` - Clean up old articles

## Usage

1. **Choose Region**: Select international news or country-specific coverage
2. **Select Topics**: Pick from popular categories (Politics, Sports, AI, Movies) or create custom topics
3. **Configure Sources**: Choose article count (5-50) and optionally exclude specific sources
4. **Get Results**: AI generates your personalized news feed with relevance scores

## AI Features

- **Intelligent Source Selection**: AI analyzes your topics and region to recommend the most relevant news sources
- **Content Analysis**: Each article is scored for relevance, credibility, and quality
- **Personalized Ranking**: Articles are ranked based on your specific interests and preferences
- **Quality Filtering**: Only high-quality, credible articles make it to your feed

## License

MIT License - see LICENSE file for details

## Support

For issues and questions, please check the documentation or contact support.