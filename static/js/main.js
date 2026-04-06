/*
 * main.js — Global JavaScript for OpenCourt.
 *
 * This file is loaded on every page (via base.html). Keep it lightweight —
 * only put truly global utilities here. Page-specific logic (e.g. chart
 * initialization) should go in { % block extra_js %} inside the relevant
 * template, not here.
 *
 * ApexCharts is already loaded before this file in base.html and is available
 * globally as `ApexCharts`. To render a chart on any page:
 *
 *   { % block extra_js %}
 *   <script>
 *     const options = {
 *       chart: { type: 'bar' },
 *       series: [{ name: 'Points', data: [21, 18, 24, 19] }],
 *       xaxis: { categories: ['Team A', 'Team B', 'Team C', 'Team D'] }
 *     };
 *     const chart = new ApexCharts(document.querySelector('#my-chart'), options);
 *     chart.render();
 *   </script>
 *   { % endblock %}
 *
 * ApexCharts docs: https://apexcharts.com/docs/chart-types/
 */


// Global utilities will go here

// Fix team card text contrast based on background brightness
function fixTeamCardContrast() {
  const teamCards = document.querySelectorAll('.team-card[style*="background-color"]');

  teamCards.forEach(card => {
    const style = card.getAttribute('style');
    // Match hex colors with or without alpha (6 or 8 characters)
    const colorMatch = style.match(/background-color:\s*#([a-fA-F0-9]{6})([a-fA-F0-9]{0,2})/);

    if (colorMatch) {
      const hexColor = colorMatch[1]; // Just the RGB part, ignore alpha
      const r = parseInt(hexColor.substr(0, 2), 16);
      const g = parseInt(hexColor.substr(2, 2), 16);
      const b = parseInt(hexColor.substr(4, 2), 16);

      // Calculate brightness using luminance formula
      const brightness = (0.299 * r + 0.587 * g + 0.114 * b) / 255;

      // If brightness > 0.65, consider it a light background (slightly higher threshold for better contrast)
      if (brightness > 0.65) {
        card.setAttribute('data-brightness', 'light');
      } else {
        card.setAttribute('data-brightness', 'dark');
        card.removeAttribute('data-brightness'); // Remove attribute for dark backgrounds
      }
    }
  });
}

// Run on page load and after any dynamic content changes
document.addEventListener('DOMContentLoaded', fixTeamCardContrast);
// Also run after a short delay to catch dynamically loaded content
setTimeout(fixTeamCardContrast, 100);
