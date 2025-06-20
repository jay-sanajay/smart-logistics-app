import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';
import './index.css';    // Tailwind or base styles (optional)
import './style.css';    // Your custom styles
import 'leaflet/dist/leaflet.css';  // Leaflet CSS from node_modules

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
