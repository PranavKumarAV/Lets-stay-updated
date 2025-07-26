import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { UserPreferences } from "@/pages/home";

interface SourcePreferencesProps {
  preferences: UserPreferences;
  updatePreferences: (updates: Partial<UserPreferences>) => void;
  onGenerate: () => void;
}

// Define article count options.  We summarize weekly highlights, so
// choose higher counts by default.  Remove the smaller options (5 and 10)
// and introduce a 35‑article option between 25 and 50.
const articleCounts = [
  { value: 25, label: "Concise" },
  { value: 35, label: "Standard" },
  { value: 50, label: "In‑Depth" },
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

        {/* Source Exclusions */}
        <div className="bg-surface rounded-xl p-6 shadow-md border border-gray-200">
          <h3 className="text-lg font-semibold text-secondary mb-4">Exclude Sources (Optional)</h3>
          <p className="text-gray-600 mb-4">
            Our AI automatically selects the best sources for your topics. You can exclude specific platforms if desired.
          </p>
          
          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
            {sources.map((source) => (
              <label key={source.id} className="flex items-center space-x-3 cursor-pointer">
                <Checkbox
                  checked={excludedSources.includes(source.id)}
                  onCheckedChange={(checked) => handleSourceToggle(source.id, checked as boolean)}
                />
                <div className="flex items-center space-x-2">
                  <div className={`w-8 h-8 bg-${source.color}-100 rounded-lg flex items-center justify-center`}>
                    <i className={`${source.icon} text-${source.color}-600`}></i>
                  </div>
                  <span className="text-sm font-medium">{source.name}</span>
                </div>
              </label>
            ))}
          </div>
        </div>

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
