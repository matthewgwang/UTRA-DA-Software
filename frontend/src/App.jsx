import { Routes, Route, Link } from "react-router-dom";
import React from 'react';

function Home() {
  return (
    <div className="container">
      <h1>Welcome</h1>
      <p>
        Hi, my name is <strong>Andrew</strong>.
      </p>
      <p>
        This website is a data analysis platform designed to explore, visualize,
        and interpret meaningful datasets. More features will be added over time,
        including analytics, insights, and audio narration.
      </p>
    </div>
  );
}

function Data() {
  return (
    <div className="container">
      <h1>Data</h1>
      <p>Data analysis tools and visualizations will be added here.</p>
    </div>
  );
}

export default function App() {
  return (
    <>
      <nav>
        <Link to="/">Home</Link>
        <Link to="/data">Data</Link>
      </nav>

      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/data" element={<Data />} />
      </Routes>
    </>
  );
}
