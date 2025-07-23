import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { UserPreferences } from "@/pages/home";

interface TopicSelectionProps {
  preferences: UserPreferences;
  updatePreferences: (updates: Partial<UserPreferences>) => void;
  onNext: () => void;
}

const predefinedTopics = [
  { id: "politics", name: "Politics", icon: "fas fa-landmark", color: "red", description: "Elections, policies, government" },
  { id: "sports", name: "Sports", icon: "fas fa-football-ball", color: "green", description: "Games, tournaments, athletes" },
  { id: "ai", name: "AI Advancement", icon: "fas fa-robot", color: "purple", description: "Technology, research, innovation" },
  { id: "movies", name: "Movies", icon: "fas fa-film", color: "yellow", description: "Releases, reviews, entertainment" },
];

export function TopicSelection({ preferences, updatePreferences, onNext }: TopicSelectionProps) {
  const [customTopic, setCustomTopic] = useState("");
  const [selectedTopics, setSelectedTopics] = useState<string[]>(preferences.topics);

  const handleTopicToggle = (topicId: string) => {
    const updatedTopics = selectedTopics.includes(topicId)
      ? selectedTopics.filter(t => t !== topicId)
      : [...selectedTopics, topicId];
    
    setSelectedTopics(updatedTopics);
    updatePreferences({ topics: updatedTopics });
  };

  const addCustomTopic = () => {
    if (customTopic.trim() && customTopic.length <= 25 && !selectedTopics.includes(customTopic.trim())) {
      const updatedTopics = [...selectedTopics, customTopic.trim()];
      setSelectedTopics(updatedTopics);
      updatePreferences({ topics: updatedTopics });
      setCustomTopic("");
    }
  };

  const removeTopic = (topic: string) => {
    const updatedTopics = selectedTopics.filter(t => t !== topic);
    setSelectedTopics(updatedTopics);
    updatePreferences({ topics: updatedTopics });
  };

  const canProceed = selectedTopics.length > 0;

  return (
    <div>
      <div className="text-center mb-8">
        <h2 className="text-3xl font-bold text-secondary mb-4">Select Your Topics</h2>
        <p className="text-gray-600 max-w-2xl mx-auto">
          Choose from predefined categories or create your own custom topic to stay updated on what matters most to you.
        </p>
      </div>

      {/* Predefined Topics */}
      <div className="max-w-5xl mx-auto mb-8">
        <h3 className="text-lg font-semibold text-secondary mb-4">Popular Categories</h3>
        <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-4">
          {predefinedTopics.map((topic) => (
            <div
              key={topic.id}
              className="cursor-pointer"
              onClick={() => handleTopicToggle(topic.id)}
            >
              <div
                className={`bg-surface rounded-xl p-6 shadow-md border transition-all ${
                  selectedTopics.includes(topic.id)
                    ? "border-primary shadow-lg bg-blue-50"
                    : "border-gray-200 hover:border-primary hover:shadow-lg"
                }`}
              >
                <div className="text-center">
                  <div className={`w-12 h-12 bg-${topic.color}-100 rounded-lg flex items-center justify-center mx-auto mb-3`}>
                    <i className={`${topic.icon} text-${topic.color}-600 text-xl`}></i>
                  </div>
                  <h4 className="font-semibold text-secondary">{topic.name}</h4>
                  <p className="text-sm text-gray-600 mt-1">{topic.description}</p>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Custom Topic */}
      <div className="max-w-2xl mx-auto mb-8">
        <h3 className="text-lg font-semibold text-secondary mb-4">Or Create Custom Topic</h3>
        <div className="bg-surface rounded-xl p-6 shadow-md border border-gray-200">
          <div className="flex items-center space-x-4">
            <div className="flex-1">
              <Input
                type="text"
                placeholder="e.g., decisions by trump, climate change..."
                maxLength={25}
                value={customTopic}
                onChange={(e) => setCustomTopic(e.target.value)}
                onKeyPress={(e) => e.key === "Enter" && addCustomTopic()}
              />
              <div className="flex justify-between items-center mt-2">
                <span className="text-sm text-gray-500">Create your own topic</span>
                <span className="text-sm text-gray-400">{customTopic.length}/25</span>
              </div>
            </div>
            <Button
              onClick={addCustomTopic}
              disabled={!customTopic.trim() || customTopic.length > 25}
              className="bg-accent text-white hover:bg-orange-600"
            >
              <i className="fas fa-plus"></i>
            </Button>
          </div>
        </div>
      </div>

      {/* Selected Topics Display */}
      {selectedTopics.length > 0 && (
        <div className="max-w-3xl mx-auto mb-8">
          <h3 className="text-lg font-semibold text-secondary mb-2">
            Selected Topics <span className="text-sm font-normal text-gray-600">({selectedTopics.length})</span>
          </h3>
          <p className="text-sm text-gray-600 mb-4">Click the × button to remove any topic you don't want</p>
          <div className="flex flex-wrap gap-3">
            {selectedTopics.map((topic) => (
              <div
                key={topic}
                className="flex items-center space-x-2 bg-primary text-white px-4 py-2 rounded-full text-sm shadow-sm"
              >
                <span>{predefinedTopics.find(t => t.id === topic)?.name || topic}</span>
                <button
                  className="ml-2 hover:text-red-200 hover:bg-red-500 rounded-full p-1.5 transition-colors bg-white/20 text-white"
                  onClick={() => removeTopic(topic)}
                  title={`Remove ${predefinedTopics.find(t => t.id === topic)?.name || topic}`}
                >
                  <i className="fas fa-times text-sm font-bold"></i>
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="text-center">
        <Button
          onClick={onNext}
          disabled={!canProceed}
          className="bg-primary text-white px-8 py-3 font-medium hover:bg-blue-700"
        >
          Continue to Sources
          <i className="fas fa-arrow-right ml-2"></i>
        </Button>
      </div>
    </div>
  );
}
