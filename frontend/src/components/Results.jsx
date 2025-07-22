import React from "react";

const Results = ({ results }) => {
  return (
    <div className="p-4">
      <h2 className="text-2xl font-bold mb-4">Top News Results</h2>
      {results.length === 0 ? (
        <p>No results found.</p>
      ) : (
        <ul className="space-y-4">
          {results.map((item, index) => (
            <li key={index} className="border-b pb-2">
              <a
                href={item.link}
                target="_blank"
                rel="noopener noreferrer"
                className="text-blue-600 hover:underline"
              >
                {item.title}
              </a>
              <p className="text-sm text-gray-600">{item.source}</p>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
};

export default Results;