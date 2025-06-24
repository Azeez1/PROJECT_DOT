let dataset = rows;
renderCharts(dataset);

// when table filters change, redraw with the *filtered* subset
document.addEventListener("tableFiltered", e => {
  dataset = e.detail;
  renderCharts(dataset);
});
