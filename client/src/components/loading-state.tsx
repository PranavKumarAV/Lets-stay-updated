export function LoadingState() {
  return (
    <div className="text-center py-16">
      <div className="w-16 h-16 bg-primary rounded-full flex items-center justify-center mx-auto mb-6 animate-pulse">
        <i className="fas fa-brain text-white text-2xl"></i>
      </div>
      <h2 className="text-2xl font-bold text-secondary mb-4">AI is Curating Your News</h2>
      <p className="text-gray-600 mb-8 max-w-md mx-auto">
        Our intelligent system is analyzing thousands of articles to bring you the most relevant and credible news.
      </p>
      
      <div className="max-w-md mx-auto space-y-4">
        <div className="flex items-center justify-between p-4 bg-surface rounded-lg shadow-sm">
          <span className="text-sm text-gray-600">Scanning news sources...</span>
          <i className="fas fa-check text-success"></i>
        </div>
        <div className="flex items-center justify-between p-4 bg-surface rounded-lg shadow-sm">
          <span className="text-sm text-gray-600">Analyzing relevance...</span>
          <div className="w-4 h-4 border-2 border-primary border-t-transparent rounded-full animate-spin"></div>
        </div>
        <div className="flex items-center justify-between p-4 bg-gray-100 rounded-lg">
          <span className="text-sm text-gray-400">Ranking articles...</span>
          <div className="w-4 h-4 border-2 border-gray-300 border-t-transparent rounded-full"></div>
        </div>
      </div>
    </div>
  );
}
