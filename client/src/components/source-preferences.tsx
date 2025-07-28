import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { UserPreferences } from "@/pages/home";

interface SourcePreferencesProps {
  preferences: UserPreferences;
  updatePreferences: (updates: Partial<UserPreferences>) => void;
  onGenerate: () => void;
}

// Define article count options.  We provide smaller counts to reduce
// API usage: 5, 10 and 15 articles.  These correspond to concise,
// standard and in‑depth summaries.  Avoid offering large counts like
// 25–50 which can exhaust the free tier of NewsAPI.
const articleCounts = [
  { value: 5, label: "Concise" },
  { value: 10, label: "Standard" },
  { value: 15, label: "In‑Depth" },
];

const sources = [
  { id: "reddit", name: "Reddit", icon: "fab fa-reddit", color: "orange" },
  { id: "substack", name: "Substack", icon: "fas fa-newspaper", color: "green" },
  { id: "traditional", name: "Traditional Media", icon: "fas fa-globe", color: "gray" },
  { id: "bbc", name: "BBC News", icon: "fas fa-broadcast-tower", color: "red" },
  { id: "reuters", name: "Reuters", icon: "fas fa-globe-americas", color: "blue" },
  { id: "npr", name: "NPR", icon: "fas fa-microphone", color: "purple" },
];

export function SourcePreferences({ preferences, updatePreferences, onGenerate }: SourcePreferencesProps) {
  const [articleCount, setArticleCount] = useState(preferences.articleCount);
  const [excludedSources, setExcludedSources] = useState<string[]>(preferences.excludedSources);

  // Determine if the user selected a country-specific (local) news region.  In
  // older versions we disabled custom source selection for local mode.  The
  // application now relies solely on the NewsAPI without per-source controls,
  // so this flag is currently unused but retained for potential future
  // enhancements.
  const isLocal = preferences.region === "country";

  const handleArticleCountChange = (count: number) => {
    setArticleCount(count);
    updatePreferences({ articleCount: count });
  };

  const handleSourceToggle = (sourceId: string, checked: boolean) => {
    const updated = checked 
      ? [...excludedSources, sourceId]
      : excludedSources.filter(s => s !== sourceId);
    
    setExcludedSources(updated);
    updatePreferences({ excludedSources: updated });
  };

  return (
    <div>
      <div className="text-center mb-8">
        <h2 className="text-3xl font-bold text-secondary mb-4">Configure News Sources</h2>
        <p className="text-gray-600 max-w-2xl mx-auto">
          Choose how many articles you want and optionally exclude specific news sources. Our AI will select the most relevant sources for your topics.
        </p>
      </div>

      <div className="max-w-4xl mx-auto space-y-8">
        {/* Article Count Selection */}
        <div className="bg-surface rounded-xl p-6 shadow-md border border-gray-200">
          <h3 className="text-lg font-semibold text-secondary mb-4">Number of Articles</h3>
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4">
            {articleCounts.map((option) => (
              <div
                key={option.value}
                className="cursor-pointer"
                onClick={() => handleArticleCountChange(option.value)}
              >
                <div
                  className={`text-center p-4 border-2 rounded-lg transition-colors ${
                    articleCount === option.value
                      ? "border-primary bg-blue-50"
                      : "border-gray-200 hover:border-primary"
                  }`}
                >
                  <div className="text-2xl font-bold text-primary mb-1">{option.value}</div>
                  <div className="text-sm text-gray-600">{option.label}</div>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* The source exclusion section has been removed.  Previously users could
            exclude individual sources or see a message indicating that
            exclusions were disabled for local mode.  Since the application
            now fetches news solely based on the NewsAPI without
            per‑source controls, there is no longer a need for this UI. */}

        {/* AI Source Selection Info */}
        <div className="bg-blue-50 rounded-xl p-6 border border-blue-200">
          <div className="flex items-start space-x-3">
            <div className="w-8 h-8 bg-blue-100 rounded-lg flex items-center justify-center flex-shrink-0 mt-1">
              <i className="fas fa-brain text-blue-600"></i>
            </div>
            <div>
              <h4 className="font-semibold text-blue-900 mb-2">AI-Powered Source Selection</h4>
              <p className="text-blue-800 text-sm">
                Our AI analyzes your topics and automatically selects the most relevant and credible sources. We consider factors like:
              </p>
              <ul className="text-blue-800 text-sm mt-2 space-y-1">
                <li>• Source credibility and reputation</li>
                <li>• Topic relevance and expertise</li>
                <li>• Content freshness and engagement</li>
                <li>• Diversity of perspectives</li>
              </ul>
            </div>
          </div>
        </div>
      </div>

      <div className="text-center mt-8">
        <Button
          onClick={onGenerate}
          className="bg-primary text-white px-8 py-3 font-medium hover:bg-blue-700"
        >
          Generate News Feed
          <i className="fas fa-magic ml-2"></i>
        </Button>
      </div>
    </div>
  );
}
