import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App'
import './styles/index.css'

// Auto-reload on stale dynamic chunk import after a new deployment
window.addEventListener('vite:preloadError', (event) => {
  console.warn('[Vite] Dynamic import chunk failed (new deployment detected). Reloading to fetch latest assets...', event);
  window.location.reload();
});

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)
