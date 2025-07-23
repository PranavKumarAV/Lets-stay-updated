# Deployment Guide for "Let's Stay Updated"

This guide will help you deploy the "Let's Stay Updated" news aggregator on Render.com.

## Prerequisites

1. GitHub account
2. Render.com account (free tier available)
3. API key (Groq free OR OpenAI paid)
4. PostgreSQL database (Render provides free PostgreSQL)

## Step-by-Step Deployment

### 1. Upload to GitHub

1. Create a new repository on GitHub named "Lets-stay-updated"
2. Upload all the files from this folder to your GitHub repository
3. Make sure all files are committed and pushed

### 2. Create PostgreSQL Database on Render

1. Go to [Render.com](https://render.com) and sign in
2. Click "New +" → "PostgreSQL"
3. Configure your database:
   - **Name**: `lets-stay-updated-db`
   - **Database**: `lets_stay_updated`
   - **User**: `news_user` (or any name you prefer)
   - **Region**: Choose closest to your users
   - **Plan**: Free (or paid for better performance)
4. Click "Create Database"
5. **Important**: Copy the "External Database URL" - you'll need this for the web service

### 3. Get Your API Key

**Option A: Groq API (Free)**
1. Go to [Groq Console](https://console.groq.com)
2. Sign in or create account
3. Create new API key
4. Copy the key (starts with `gsk_`)

**Option B: OpenAI API (Paid)**
1. Go to [OpenAI Platform](https://platform.openai.com/api-keys)
2. Sign in or create account
3. Click "Create new secret key"
4. Copy the key (starts with `sk-`)

### 4. Create Web Service on Render

1. In Render dashboard, click "New +" → "Web Service"
2. Connect your GitHub repository
3. Configure the service:

   **Basic Settings:**
   - **Name**: `lets-stay-updated`
   - **Region**: Same as your database
   - **Branch**: `main` (or your default branch)
   - **Root Directory**: Leave empty
   - **Runtime**: `Node`

   **Build & Deploy:**
   - **Build Command**: `npm install && npm run build`
   - **Start Command**: `npm start`

   **Environment Variables:**
   Click "Advanced" and add these:
   
   **For Groq (Free):**
   ```
   NODE_ENV=production
   DATABASE_URL=[Paste the External Database URL from step 2]
   GROQ_API_KEY=[Your Groq API key from step 3]
   LLM_PROVIDER=groq
   PORT=5000
   ```

   **For OpenAI (Paid):**
   ```
   NODE_ENV=production
   DATABASE_URL=[Paste the External Database URL from step 2]
   OPENAI_API_KEY=[Your OpenAI API key from step 3]
   LLM_PROVIDER=openai
   PORT=5000
   ```

4. Click "Create Web Service"

### 5. Deploy

1. Render will automatically start building and deploying
2. Wait for the build to complete (usually 2-5 minutes)
3. Once deployed, you'll get a URL like: `https://lets-stay-updated.onrender.com`

## Cost Comparison

### Free Option (Groq)
- **Render Database**: Free
- **Render Web Service**: Free
- **Groq API**: Free
- **Total**: $0/month

### Paid Option (OpenAI)
- **Render Database**: Free
- **Render Web Service**: Free  
- **OpenAI API**: ~$2-10/month
- **Total**: $2-10/month

## Troubleshooting

### Common Issues

**Build fails:**
- Make sure all files were uploaded to GitHub correctly
- Check that `package.json` is in the root directory

**Database connection errors:**
- Verify the `DATABASE_URL` environment variable is correct
- Ensure your PostgreSQL database is running on Render

**API errors:**
- Verify your API key is set correctly
- Check that `LLM_PROVIDER` matches your API (groq or openai)
- For OpenAI: Make sure you have credits in your account

**App starts but shows errors:**
- Check the logs in Render dashboard under "Logs" tab
- Make sure all environment variables are set

### Checking Logs

1. Go to your Render dashboard
2. Click on your web service  
3. Go to "Logs" tab to see real-time logs
4. Look for any error messages

## Testing Your Deployment

1. Visit your Render URL
2. Test the complete flow:
   - Select region (International or Country-specific)
   - Choose topics
   - Configure source preferences
   - Generate news articles

If everything works, you now have a live news aggregation website!

## Optional Upgrades

For better performance, you can upgrade to paid plans:
- **Database**: Paid PostgreSQL for better performance
- **Web Service**: Paid plan for no sleep mode and faster response
- **Custom Domain**: Add your own domain name

This setup gives you a fully functional news aggregation website accessible to anyone on the internet!