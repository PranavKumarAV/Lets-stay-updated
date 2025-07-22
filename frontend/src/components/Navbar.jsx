import React from "react";
import { Link } from "react-router-dom";

const Navbar = () => (
  <nav className="bg-blue-600 p-4 text-white">
    <div className="max-w-7xl mx-auto flex items-center justify-between">
      <Link to="/" className="text-xl font-bold">
        Let’s Stay Updated
      </Link>
      <div>
        <Link to="/" className="mr-4 hover:underline">
          Home
        </Link>
        <a
          href="https://github.com/your-repo-link"
          target="_blank"
          rel="noopener noreferrer"
          className="hover:underline"
        >
          GitHub
        </a>
      </div>
    </div>
  </nav>
);

export default Navbar;