import { useState } from "react";
import { StepIndicator } from "@/components/step-indicator";
import { RegionSelection } from "@/components/region-selection";
import { TopicSelection } from "@/components/topic-selection";
import { SourcePreferences } from "@/components/source-preferences";
import { NewsResults } from "@/components/news-results";
import { LoadingState } from "@/components/loading-state";

export type Step = 1 | 2 | 3 | 4 | "loading";

export interface UserPreferences {
  region: string;
  country?: string;
  topics: string[];
  articleCount: number;
  excludedSources: string[];
}

export default function Home() {
  const [currentStep, setCurrentStep] = useState<Step>(1);
  const [preferences, setPreferences] = useState<UserPreferences>({
    region: "",
    country: "",
    topics: [],
    // Default to 25 articles for weekly summaries
    // Default to 10 articles for weekly summaries.  The user can
    // choose 5 or 15 on the next step if they prefer.
    articleCount: 10,
    excludedSources: [],
  });

  const updatePreferences = (updates: Partial<UserPreferences>) => {
    setPreferences(prev => ({ ...prev, ...updates }));
  };

  const nextStep = () => {
    if (currentStep === 1) setCurrentStep(2);
    else if (currentStep === 2) setCurrentStep(3);
    else if (currentStep === 3) {
      setCurrentStep("loading");
      // Simulate AI processing, then go to results
      setTimeout(() => setCurrentStep(4), 3000);
    }
  };

  const generateNews = () => {
    setCurrentStep("loading");
    // The actual API call will be handled by the NewsResults component
    // We just need to navigate to the results page
    setTimeout(() => setCurrentStep(4), 1000);
  };

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="bg-surface shadow-md border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            <div className="flex items-center space-x-3">
              {/* Display a newspaper emoji for a more vibrant header */}
              <span className="text-3xl">🗞️</span>
              <h1 className="text-xl font-bold text-secondary">Let's Stay Updated</h1>
            </div>
            <div className="flex items-center space-x-4">
              <span className="text-sm text-gray-600">AI-Powered News Curation</span>
              <div className="w-8 h-8 bg-gray-200 rounded-full flex items-center justify-center">
                <i className="fas fa-user text-gray-600 text-sm"></i>
              </div>
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <StepIndicator currentStep={currentStep} />

        {currentStep === 1 && (
          <RegionSelection
            preferences={preferences}
            updatePreferences={updatePreferences}
            onNext={nextStep}
          />
        )}

        {currentStep === 2 && (
          <TopicSelection
            preferences={preferences}
            updatePreferences={updatePreferences}
            onNext={nextStep}
          />
        )}

        {currentStep === 3 && (
          <SourcePreferences
            preferences={preferences}
            updatePreferences={updatePreferences}
            onGenerate={generateNews}
          />
        )}

        {currentStep === "loading" && <LoadingState />}

        {currentStep === 4 && (
          <NewsResults
            preferences={preferences}
            onModifySearch={() => setCurrentStep(1)}
          />
        )}
      </main>

      {/* Footer */}
      <footer className="bg-secondary text-white py-8 mt-16">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center">
            <div className="flex items-center justify-center space-x-2 mb-4">
              <span className="text-xl">🗞️</span>
              <span className="font-semibold">Let's Stay Updated</span>
            </div>
            {/* About the creator */}
            <p className="text-gray-300 text-sm mb-4">
              I’m Pranav Venkatesan, just a curious guy trying to work and develop AI‑related projects.
            </p>
            <div className="flex items-center justify-center space-x-6 text-sm">
              <a
                href="https://github.com/PranavKumarAV"
                target="_blank"
                rel="noopener noreferrer"
                className="hover:text-primary transition-colors underline"
              >
                GitHub
              </a>
              <a
                href="https://www.linkedin.com/in/pranav31/"
                target="_blank"
                rel="noopener noreferrer"
                className="hover:text-primary transition-colors underline"
              >
                LinkedIn
              </a>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
}
