# Deployment Guide for Render.com

This guide will help you deploy the AI-Powered News Aggregator on Render.com.

## Prerequisites

1. GitHub account
2. Render.com account (free tier available)
3. OpenAI API key
4. PostgreSQL database (Render provides free PostgreSQL)

## Step-by-Step Deployment

### 1. Upload to GitHub

1. Create a new repository on GitHub
2. Upload all the files from this folder to your GitHub repository
3. Make sure all files are committed and pushed

### 2. Create PostgreSQL Database on Render

1. Go to [Render.com](https://render.com) and sign in
2. Click "New +" → "PostgreSQL"
3. Configure your database:
   - **Name**: `news-aggregator-db`
   - **Database**: `news_aggregator`
   - **User**: `news_user` (or any name you prefer)
   - **Region**: Choose closest to your users
   - **Plan**: Free (or paid for better performance)
4. Click "Create Database"
5. **Important**: Copy the "External Database URL" - you'll need this for the web service

### 3. Create Web Service on Render

1. In Render dashboard, click "New +" → "Web Service"
2. Connect your GitHub repository
3. Configure the service:

   **Basic Settings:**
   - **Name**: `news-aggregator`
   - **Region**: Same as your database
   - **Branch**: `main` (or your default branch)
   - **Root Directory**: Leave empty
   - **Runtime**: `Node`

   **Build & Deploy:**
   - **Build Command**: `npm install && npm run build`
   - **Start Command**: `npm start`

   **Environment Variables:**
   Click "Advanced" and add these environment variables:
   
   ```
   NODE_ENV=production
   DATABASE_URL=[Paste the External Database URL from step 2]
   OPENAI_API_KEY=[Your OpenAI API key from https://platform.openai.com/api-keys]
   PORT=5000
   ```

4. Click "Create Web Service"

### 4. Get Your OpenAI API Key

1. Go to [OpenAI Platform](https://platform.openai.com/api-keys)
2. Sign in or create an account
3. Click "Create new secret key"
4. Copy the key and add it to your Render environment variables

### 5. Deploy

1. Render will automatically start building and deploying
2. Wait for the build to complete (usually 2-5 minutes)
3. Once deployed, you'll get a URL like: `https://your-app-name.onrender.com`

## Troubleshooting

### Common Issues and Solutions

**Build fails with dependency errors:**
- Make sure all files were uploaded to GitHub correctly
- Check that `package.json` is in the root directory

**Database connection errors:**
- Verify the `DATABASE_URL` environment variable is set correctly
- Ensure your PostgreSQL database is running on Render

**OpenAI API errors:**
- Verify your `OPENAI_API_KEY` is set correctly
- Make sure you have credits in your OpenAI account
- Check that the API key has the right permissions

**App starts but shows errors:**
- Check the logs in Render dashboard under "Logs" tab
- Make sure all environment variables are set

### Checking Logs

1. Go to your Render dashboard
2. Click on your web service
3. Go to "Logs" tab to see real-time logs
4. Look for any error messages

## Post-Deployment

### Testing Your Application

1. Visit your Render URL
2. Test the complete flow:
   - Select region (International or Country-specific)
   - Choose topics
   - Configure source preferences
   - Generate news articles

### Monitoring

- Use Render's built-in monitoring
- Check logs regularly for any issues
- Monitor your OpenAI API usage

## Scaling (Optional)

If you need better performance:

1. **Database**: Upgrade to a paid PostgreSQL plan
2. **Web Service**: Upgrade to a paid plan for:
   - Faster builds
   - No sleep mode
   - Better performance
   - Custom domains

## Custom Domain (Optional)

1. Purchase a domain name
2. In Render dashboard, go to your web service
3. Click "Settings" → "Custom Domains"
4. Add your domain and follow DNS configuration instructions

## Support

If you encounter issues:

1. Check Render's documentation: [render.com/docs](https://render.com/docs)
2. Check OpenAI's documentation: [platform.openai.com/docs](https://platform.openai.com/docs)
3. Review the application logs in Render dashboard

## Cost Estimation

**Free Tier:**
- Render PostgreSQL: Free (1GB storage, some limitations)
- Render Web Service: Free (750 hours/month, sleeps after 15min inactivity)
- OpenAI API: Pay-per-use (typically $0.50-$2/month for moderate usage)

**Total estimated cost for moderate usage: $0.50-$2/month**

This deployment setup will give you a fully functional news aggregation website accessible to anyone on the internet!