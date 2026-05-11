const form = document.getElementById('planner-form');
const statusEl = document.getElementById('status');
const resultsEl = document.getElementById('results');
const historyEl = document.getElementById('history');

const formatCurrency = (value) => new Intl.NumberFormat('en-IN', {
  style: 'currency',
  currency: 'INR',
  maximumFractionDigits: 0,
}).format(value);

function renderPlan(data) {
  resultsEl.classList.remove('hidden');
  document.getElementById('plan-summary').textContent = data.planner.summary;
  document.getElementById('budget-tip').textContent = data.optimizer.savings_tip;
  document.getElementById('predicted-total').textContent = `Predicted total spend: ${formatCurrency(data.optimizer.predicted_total)}`;
  document.getElementById('knowledge-answer').textContent = data.researcher.answer;

  document.getElementById('vendor-categories').innerHTML = data.planner.vendor_categories
    .map((cat) => `<span class="chip">${cat}</span>`)
    .join('');

  document.getElementById('budget-breakdown').innerHTML = data.optimizer.allocations
    .map((item) => `
      <div class="budget-row">
        <strong>${item.category}</strong>
        <div>${formatCurrency(item.amount)} · ${item.percent}%</div>
        <div class="bar"><span style="width:${Math.min(item.percent, 100)}%"></span></div>
      </div>
    `)
    .join('');

  document.getElementById('timeline').innerHTML = data.planner.timeline
    .map((phase) => `
      <div class="timeline-phase">
        <strong>${phase.phase}</strong>
        <ul>${phase.tasks.map((task) => `<li>${task}</li>`).join('')}</ul>
      </div>
    `)
    .join('');

  document.getElementById('checklist').innerHTML = data.planner.checklist
    .map((item) => `<li>${item}</li>`)
    .join('');

  document.getElementById('vendors').innerHTML = data.vendors
    .map((vendor) => `
      <div class="vendor-card">
        <strong>${vendor.name}</strong>
        <div>${vendor.category} · Rating ${vendor.rating} · ${formatCurrency(vendor.base_price)}</div>
        <div>Match score: ${vendor.match_score}</div>
        <div class="vendor-tags">${vendor.tags.map((tag) => `<span class="tag">${tag}</span>`).join('')}</div>
      </div>
    `)
    .join('');

  document.getElementById('knowledge-sources').innerHTML = data.researcher.sources
    .map((src) => `<li>${src.title} — ${src.source}</li>`)
    .join('');
}

async function loadHistory() {
  statusEl.textContent = 'Loading recent plans...';
  const response = await fetch('/api/history');
  const history = await response.json();
  historyEl.innerHTML = history.length
    ? history
        .map(
          (item) => `
      <div class="history-item">
        <strong>${item.event_type.toUpperCase()} · ${item.city}</strong>
        <p>${formatCurrency(item.budget)} · ${item.preferences}</p>
        <small>${item.created_at}</small>
      </div>
    `,
        )
        .join('')
    : '<p>No plans saved yet.</p>';
  statusEl.textContent = 'Recent plans loaded.';
}

document.getElementById('load-history').addEventListener('click', loadHistory);

form.addEventListener('submit', async (event) => {
  event.preventDefault();
  const formData = new FormData(form);
  const payload = Object.fromEntries(formData.entries());
  payload.budget = Number(payload.budget);

  statusEl.textContent = 'Generating event plan using planner, optimizer, and knowledge agents...';
  try {
    const response = await fetch('/api/plan', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    if (!response.ok) throw new Error('Failed to generate plan');
    const data = await response.json();
    renderPlan(data);
    statusEl.textContent = 'Plan generated successfully.';
    loadHistory();
  } catch (error) {
    console.error(error);
    statusEl.textContent = 'Something went wrong while creating the plan.';
  }
});
