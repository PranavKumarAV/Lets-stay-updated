import React from "react";
import { RotatingLines } from "react-loader-spinner";

const Loading = () => {
  return (
    <div className="flex flex-col items-center justify-center min-h-screen">
      <RotatingLines
        strokeColor="blue"
        strokeWidth="5"
        animationDuration="0.75"
        width="96"
        visible={true}
      />
      <p className="mt-4 text-gray-700 font-semibold">Fetching news summary...</p>
    </div>
  );
};

export default Loading;