import ShipMap from './Map';
import githubLogo from './assets/github.png';
import { Analytics } from '@vercel/analytics/react';

function App() {
  return (
    <div className="relative w-full h-screen">
      <ShipMap />
      <a href="https://github.com/wrufay/dfo_ocean_data" target="_blank" rel="noreferrer"
        className="absolute bottom-4 left-[19rem] z-10 opacity-60 hover:opacity-100">
        <img src={githubLogo} alt="GitHub" className="w-6 h-6" />
      </a>
      <Analytics />
    </div>
  );
}

export default App;
