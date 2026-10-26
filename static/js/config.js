/**
 * AssignCheck Dashboard - Environment Configuration
 *
 * For unified deployment on Render or running locally:
 * Leave window.__BACKEND_URL__ as empty string "" (relative API endpoints).
 *
 * For separate frontend deployment on Vercel:
 * Option 1 (Recommended): Set window.__BACKEND_URL__ below to your Render backend URL:
 *   window.__BACKEND_URL__ = "https://your-service-name.onrender.com";
 * Option 2: Rely on vercel.json reverse-proxy rewrites (/api/:path* -> Render URL).
 * Option 3: Configure via browser localStorage:
 *   localStorage.setItem('assigncheck_backend_url', 'https://your-service-name.onrender.com');
 */
window.__BACKEND_URL__ = window.__BACKEND_URL__ || "";
