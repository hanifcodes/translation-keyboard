// Where the page finds the Translation Keyboard server.
//
// Leave apiBase empty ("") and the page works out the server by itself:
//   1. the same address the page came from (when FastAPI serves the page), then
//   2. http://localhost:8000 (when you use VS Code Live Server locally).
// If no server answers, the page opens in Preview mode with placeholder output.
//
// For GitHub Pages, put your Render address here, for example:
//   apiBase: "https://translation-keyboard.onrender.com"
// and add your Pages address to ALLOWED_ORIGINS on the server.
//
// Never put an API key in this file: everything here is public.
window.TK_CONFIG = {
  apiBase: "",
};
