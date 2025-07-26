import { useQuery } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useToast } from "@/hooks/use-toast";
import { UserPreferences } from "@/pages/home";
import { newsApi, type GenerateNewsResponse } from "@/lib/api";

interface NewsResultsProps {
  preferences: UserPreferences;
  onModifySearch: () => void;
}

export function NewsResults({ preferences, onModifySearch }: NewsResultsProps) {
  const { toast } = useToast();

  const { data: newsData, isLoading, error, refetch } = useQuery<GenerateNewsResponse>({
    queryKey: ["/api/news/generate", preferences],
    queryFn: async () => {
      return newsApi.generateNews({
        region: preferences.region,
        country: preferences.country,
        topics: preferences.topics,
        article_count: preferences.articleCount,
        excluded_sources: preferences.excludedSources,
      });
    },
    retry: 1,
  });

  const handleRefresh = async () => {
    try {
      await refetch();
      toast({
        title: "News Updated",
        description: "Your feed has been refreshed with the latest articles.",
      });
    } catch (error) {
      toast({
        title: "Refresh Failed",
        description: "Unable to refresh the news feed. Please try again.",
        variant: "destructive",
      });
    }
  };

  if (error) {
    return (
      <div className="text-center py-16">
        <div className="w-16 h-16 bg-red-100 rounded-full flex items-center justify-center mx-auto mb-6">
          <i className="fas fa-exclamation-triangle text-red-600 text-2xl"></i>
        </div>
        <h2 className="text-2xl font-bold text-secondary mb-4">Unable to Load News</h2>
        <p className="text-gray-600 mb-8 max-w-md mx-auto">
          We encountered an error while generating your news feed. Please check your internet connection and try again.
        </p>
        <div className="space-x-4">
          <Button onClick={handleRefresh} variant="outline">
            <i className="fas fa-refresh mr-2"></i>
            Try Again
          </Button>
          <Button onClick={onModifySearch}>
            <i className="fas fa-edit mr-2"></i>
            Modify Search
          </Button>
        </div>
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="space-y-6">
        <div className="mb-8">
          <Skeleton className="h-8 w-64 mb-2" />
          <Skeleton className="h-4 w-48" />
        </div>
        {[...Array(5)].map((_, i) => (
          <Card key={i} className="shadow-md">
            <CardContent className="p-6">
              <div className="flex items-start justify-between mb-4">
                <div className="flex items-center space-x-3">
                  <Skeleton className="w-8 h-8 rounded-lg" />
                  <div>
                    <Skeleton className="h-4 w-20 mb-1" />
                    <Skeleton className="h-3 w-32" />
                  </div>
                </div>
                <Skeleton className="h-6 w-20" />
              </div>
              <Skeleton className="h-6 w-full mb-3" />
              <Skeleton className="h-4 w-full mb-2" />
              <Skeleton className="h-4 w-3/4 mb-4" />
              <div className="flex items-center justify-between">
                <Skeleton className="h-4 w-32" />
                <Skeleton className="h-4 w-24" />
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    );
  }

  const articles = newsData?.articles || [];

  return (
    <div>
      <div className="mb-8">
        <div className="flex flex-col md:flex-row md:items-center md:justify-between mb-6">
          <div>
            <h2 className="text-3xl font-bold text-secondary mb-2">This Week's Highlights</h2>
            <p className="text-gray-600">AI-selected summaries based on your preferences</p>
          </div>
          <div className="flex items-center space-x-4 mt-4 md:mt-0">
            <div className="flex items-center space-x-2 text-sm text-gray-600">
              <i className="fas fa-clock"></i>
              <span>Updated {new Date(newsData?.generated_at || Date.now()).toLocaleTimeString()}</span>
            </div>
            <Button onClick={handleRefresh} variant="ghost" size="sm" className="text-primary hover:text-blue-700">
              <i className="fas fa-refresh mr-1"></i>
              Refresh
            </Button>
          </div>
        </div>

        {/* Filter Summary */}
        <Card className="mb-6">
          <CardContent className="p-4">
            <div className="flex flex-wrap items-center gap-4 text-sm">
              <div className="flex items-center space-x-2">
                <i className="fas fa-globe text-primary"></i>
                <span className="font-medium">
                  {preferences.region === "international" ? "International" : preferences.country}
                </span>
              </div>
              <div className="flex items-center space-x-2">
                <i className="fas fa-tags text-primary"></i>
                <span>{preferences.topics.join(", ")}</span>
              </div>
              <div className="flex items-center space-x-2">
                <i className="fas fa-list text-primary"></i>
                <span>Top {preferences.articleCount} articles</span>
              </div>
              <Button
                onClick={onModifySearch}
                variant="ghost"
                size="sm"
                className="text-accent hover:text-orange-600 font-medium ml-auto"
              >
                <i className="fas fa-edit mr-1"></i>
                Modify Search
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>

      {articles.length === 0 ? (
        <div className="text-center py-16">
          <div className="w-16 h-16 bg-gray-100 rounded-full flex items-center justify-center mx-auto mb-6">
            <i className="fas fa-search text-gray-400 text-2xl"></i>
          </div>
          <h3 className="text-xl font-semibold text-secondary mb-2">No Articles Found</h3>
          <p className="text-gray-600 mb-8 max-w-md mx-auto">
            We couldn't find any articles matching your criteria. Try adjusting your topics or preferences.
          </p>
          <Button onClick={onModifySearch}>
            <i className="fas fa-edit mr-2"></i>
            Modify Search
          </Button>
        </div>
      ) : (
        <div className="bg-surface rounded-xl p-6 shadow-md border border-gray-200">
          {/* Use a custom list style rather than relying on CSS bullets.  */}
          <ul className="space-y-4">
            {articles.map((article) => (
              <li key={article.id} className="flex items-start justify-between">
                <div className="flex">
                  {/* Leading symbol to differentiate each point */}
                  <span className="text-primary mr-2 mt-1">•</span>
                  <div className="pr-4 text-gray-700 max-w-prose">
                    {/* Use the summary if available, otherwise fall back to the first lines of the content */}
                    {article.summary || article.metadata?.summary || article.content.slice(0, 200) + (article.content.length > 200 ? "..." : "")}
                  </div>
                </div>
                <a
                  href={article.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-primary hover:text-blue-700 text-sm flex-shrink-0 ml-2"
                >
                  Link
                  <i className="fas fa-external-link-alt ml-1"></i>
                </a>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
