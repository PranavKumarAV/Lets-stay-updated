# Deployment Guide for Render.com

## Quick Deploy Steps

### 1. Prerequisites
- GitHub repository with this code
- OpenAI API key from https://platform.openai.com/

### 2. Deploy to Render.com

#### Option A: Automatic Deployment (Recommended)
1. **Connect Repository**: Link your GitHub repo to Render.com
2. **Configure Environment**: Add these environment variables in Render dashboard:
   ```
   OPENAI_API_KEY=your_actual_openai_key_here
   NODE_ENV=production
   ```
3. **Deploy**: Render automatically uses `render.yaml` configuration
4. **Access**: Your app will be available at `https://your-app-name.onrender.com`

#### Option B: Manual Setup
1. **Create Web Service** on Render.com
2. **Connect GitHub Repository**
3. **Configure Settings**:
   - **Build Command**: `npm install && npm run build`
   - **Start Command**: `npm start`
   - **Node Version**: 20
   - **Health Check Path**: `/health`
4. **Environment Variables**:
   - `OPENAI_API_KEY`: Your OpenAI API key
   - `NODE_ENV`: `production`
5. **Deploy**

### 3. Verify Deployment

After deployment, check:
- ✅ Health endpoint: `https://your-app.onrender.com/health`
- ✅ Main app: `https://your-app.onrender.com`
- ✅ AI features work (requires OpenAI API key)

## Configuration Files Created

### Core Deployment Files
- `render.yaml` - Render.com service configuration
- `Dockerfile` - Container deployment option
- `.dockerignore` - Docker build optimization
- `.env.example` - Environment variable template

### Build Configuration
- Health check endpoint at `/health`
- Production build optimizations
- Static file serving configuration
- Environment-based configuration

## Environment Variables

### Required
```env
OPENAI_API_KEY=your_openai_api_key_here
```

### Optional
```env
NODE_ENV=production
PORT=5000
DATABASE_URL=postgresql://user:pass@host:port/db
```

## Build Process

The application builds in two stages:
1. **Frontend**: Vite builds React app to `dist/public/`
2. **Backend**: esbuild bundles server to `dist/index.js`

Total build time: ~15 seconds
Output size: ~400KB (compressed)

## Troubleshooting

### Common Issues

**Build Fails**
- Check Node.js version (requires 18+)
- Verify all dependencies are installed
- Run `npm run check` for TypeScript errors

**AI Features Don't Work**
- Verify `OPENAI_API_KEY` is set correctly
- Check API key has sufficient credits
- Monitor server logs for OpenAI errors

**Health Check Fails**
- Ensure app starts on correct port (PORT env var)
- Check server logs for startup errors
- Verify `/health` endpoint responds

### Support
- Check Render.com deployment logs
- Monitor application logs in Render dashboard
- Verify environment variables are set correctly

## Production Optimizations

- ✅ Static asset caching
- ✅ Gzip compression
- ✅ Health monitoring
- ✅ Error handling
- ✅ Request logging
- ✅ Production builds
- ✅ Environment configuration