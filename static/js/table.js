export async function buildTable(selector, columns) {
  const table = document.querySelector(selector);
  const headerRow = document.getElementById("header-row");
  const filterRow = document.getElementById("filter-row");
  const tbody = table.querySelector("tbody");

  // Build the header cells
  headerRow.innerHTML = columns.map(c => `<th>${c}</th>`).join("");

  const filters = window.activeFilters || (window.activeFilters = {}); // {col: value}

  // initial fetch + render
  let df = await fetchData(filters);
  rows = df;               // expose globally for charts.js
  render(df);              // draw table
  drawChart(df);           // draw stacked-bar / trend line

  /* 1️⃣  after first load populate a <select> for each column    */
  columns.forEach(col => {
    const unique = [...new Set(df.map(r => r[col]))]
                     .filter(x => x != null)
                     .sort();
    const cell = document.createElement("th");
    const sel  = document.createElement("select");
    sel.dataset.col = col;
    sel.innerHTML = `<option value="">All</option>` +
                    unique.map(v => `<option>${v}</option>`).join("");
    cell.appendChild(sel);
    filterRow.appendChild(cell);

    /* ↓ 2️⃣  when user picks a value, refetch + redraw */
    sel.addEventListener("change", async e => {
      const col = e.target.dataset.col;
      if (e.target.value) filters[col] = e.target.value;
      else                delete filters[col];
      const fresh = await fetchData(filters);
      rows = fresh;
      render(fresh);
      drawChart(fresh);
    });
  });

  /* ---------------------------------------------------------- */
  async function fetchData(filters) {
    // encode filters: ?f=Col::Val (multi-param)
    const q = Object.entries(filters)
                    .map(([k,v]) => `f=${encodeURIComponent(`${k}::${v}`)}`)
                    .join("&");
    const url = `/api/${wizId}/query?table=hos${q ? "&"+q : ""}`;
    return (await fetch(url)).json();
  }

  function render(data){
    tbody.innerHTML = data.map(r =>
      `<tr>${columns.map(c => `<td>${r[c] ?? ''}</td>`).join('')}</tr>`
    ).join('');
    const rc = document.getElementById('row-count');
    if(rc) rc.textContent = data.length;
  }

  function drawChart(data){
    document.dispatchEvent(new CustomEvent('tableFiltered', { detail: data }));
  }
}
