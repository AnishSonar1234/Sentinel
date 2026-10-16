// Frontend Environment Configuration
// Automatically detects the current domain/host, or you can hardcode a specific URL
window.ENV = {
  API_URL: (typeof window !== "undefined" && window.location && window.location.origin)
    ? window.location.origin
    : "https://sentinel-46uf.onrender.com"
};
