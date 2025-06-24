// rows = array of plain JS objects already fetched
const rows = await (await fetch(`/api/${wizId}/query?table=hos`)).json();
let activeFilters = {};               // { colName -> value }
renderTable(rows);

/* ---------- column-header filters ---------- */
// assume each th has data-col="<field>" & a <input> or <select>
document.querySelectorAll("th .filter").forEach(ctrl => {
  ctrl.addEventListener("input", e => {
    const col = e.target.closest("th").dataset.col;
    const val = e.target.value.trim();
    if (val) activeFilters[col] = val.toLowerCase();
    else     delete activeFilters[col];           // cleared ⇒ remove filter

    // 1️⃣  recompute visible rows
    const visible = rows.filter(r =>
      Object.entries(activeFilters).every(([c,v]) =>
        String(r[c] ?? "").toLowerCase().includes(v)
      )
    );

    // 2️⃣  redraw table *and* notify charts
    renderTable(visible);
    document.dispatchEvent(new CustomEvent("tableFiltered", { detail: visible }));
  });
});

function renderTable(data) {
  const tbody = document.querySelector("#hos-tbody");
  tbody.innerHTML = data.map(r => `
    <tr>
      <td>${r.date}</td>
      <td>${r.driver}</td>
      <td>${r["Violation Type"]}</td>
      <td>${r.tags}</td>
      <td>${r.region}</td>
      <td>${r.duration}</td>
    </tr>`).join("");
  document.querySelector("#row-count").textContent = data.length;
}
