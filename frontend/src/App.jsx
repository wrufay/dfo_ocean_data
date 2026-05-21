import React from 'react';
import NoiseMap from './Map';
import githubLogo from './assets/github.png';


// Main page for front-end
function App() {
  return (
    <div className="text-center">
      <h1 className="text-sm sm:text-lg px-4 py-2 absolute z-10 bg-[#F5DFBB]/80 top-6 left-1/2 -translate-x-1/2 rounded-lg work-sans text-[#127475]">Ocean Noise Data Visualizer</h1>
      <NoiseMap />
      <a href="https://github.com/wrufay/ocean_noise_visualizer" target="_blank" rel="noreferrer" className="absolute bottom-4 left-4 z-10 opacity-67">
        <img src={githubLogo} alt="GitHub" className="w-8 h-8" />
      </a>
    </div>
  );
}

export default App;
