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

// Mobile menu toggle function
function toggleMobileMenu() {
  const menu = document.getElementById('mobile-menu');
  menu.classList.toggle('hidden');
}

// Close mobile menu when clicking outside
document.addEventListener('click', function(event) {
  const menu = document.getElementById('mobile-menu');
  const menuButton = event.target.closest('button[onclick="toggleMobileMenu()"]');

  if (!menuButton && !menu.contains(event.target)) {
    menu.classList.add('hidden');
  }
});
