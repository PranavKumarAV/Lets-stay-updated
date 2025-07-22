import { useState } from 'react';
import { useNavigate } from 'react-router-dom';

const categories = [
  'Politics',
  'Sports',
  'Advancement in AI',
  'Movies',
  'Custom'
];

const sources = ['Reddit', 'Google News', 'Substack'];

function Home() {
  const [region, setRegion] = useState('world');
  const [category, setCategory] = useState('Politics');
  const [customKeyword, setCustomKeyword] = useState('');
  const [selectedSources, setSelectedSources] = useState(sources);
  const [topK, setTopK] = useState(10);
  const navigate = useNavigate();

  const handleSubmit = (e) => {
    e.preventDefault();
    const query = {
      region,
      category,
      customKeyword,
      selectedSources,
      topK,
    };
    navigate('/results', { state: query });
  };

  const handleSourceToggle = (src) => {
    setSelectedSources(prev =>
      prev.includes(src)
        ? prev.filter(s => s !== src)
        : [...prev, src]
    );
  };

  return (
    <div className="p-6 max-w-xl mx-auto">
      <h1 className="text-2xl font-bold mb-4">Let’s Stay Updated</h1>
      <form onSubmit={handleSubmit}>
        <div className="mb-4">
          <label className="block font-semibold mb-1">Select Region:</label>
          <select value={region} onChange={(e) => setRegion(e.target.value)} className="w-full p-2 border rounded">
            <option value="world">World</option>
            <option value="country">My Country</option>
          </select>
        </div>

        <div className="mb-4">
          <label className="block font-semibold mb-1">Select Category:</label>
          <select value={category} onChange={(e) => setCategory(e.target.value)} className="w-full p-2 border rounded">
            {categories.map(cat => (
              <option key={cat} value={cat}>{cat}</option>
            ))}
          </select>
          {category === 'Custom' && (
            <input
              type="text"
              placeholder="e.g., Trump Decisions"
              maxLength={25}
              className="w-full p-2 border mt-2 rounded"
              value={customKeyword}
              onChange={(e) => setCustomKeyword(e.target.value)}
            />
          )}
        </div>

        <div className="mb-4">
          <label className="block font-semibold mb-1">Sources:</label>
          {sources.map(src => (
            <div key={src}>
              <label>
                <input
                  type="checkbox"
                  checked={selectedSources.includes(src)}
                  onChange={() => handleSourceToggle(src)}
                  className="mr-2"
                />
                {src}
              </label>
            </div>
          ))}
        </div>

        <div className="mb-4">
          <label className="block font-semibold mb-1">Number of News Items:</label>
          <select value={topK} onChange={(e) => setTopK(Number(e.target.value))} className="w-full p-2 border rounded">
            {[5, 10, 25, 50].map(num => (
              <option key={num} value={num}>{num}</option>
            ))}
          </select>
        </div>

        <button type="submit" className="bg-blue-600 text-white px-4 py-2 rounded">Get Updates</button>
      </form>
    </div>
  );
}

export default Home;
