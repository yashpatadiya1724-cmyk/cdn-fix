// Sample CDN-served JavaScript
console.log('CDN delivered this script!');
document.addEventListener('DOMContentLoaded', () => {
  const el = document.getElementById('cdn-status');
  if (el) el.textContent = 'Loaded via CDN ✓';
});
function greet(name) { return `Hello, ${name}! Delivered by CDN.`; }
