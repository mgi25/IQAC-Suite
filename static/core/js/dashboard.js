/* IQAC Suite – Dashboard UI (frontend only) */
(function () {
  const $ = (s, r = document) => r.querySelector(s);
  const $$ = (s, r = document) => Array.from(r.querySelectorAll(s));
  const px = v => Number.parseFloat(v) || 0;

  // Simple tab/anchor navigation
  function goTab(id, hash) {
    const extra = hash ? (hash.startsWith('#') ? hash.slice(1) : hash) : '';
    const suffix = extra ? (extra.startsWith('&') ? extra : `&${extra}`) : '';
    location.hash = `#${id}${suffix}`;
  }
  $('#kpiStudents')?.addEventListener('click', () => goTab('students'));
  $('#kpiClasses')?.addEventListener('click', () => goTab('profile'));
  $('#kpiOrgEvents')?.addEventListener('click', () => goTab('events', '#type=my'));
  $('#kpiPartEvents')?.addEventListener('click', () => goTab('events', '#type=participating'));
  $$('[data-go-tab="profile"]').forEach(el=>el.addEventListener('click',e=>{e.preventDefault();goTab('profile');}));
  $$('[data-go-tab="events"]').forEach(el=>el.addEventListener('click',e=>{e.preventDefault();goTab('events');}));

  // Donut: Performance / Contribution
  let donut, currentView = 'performance';
  const ctx = $('#donutChart')?.getContext('2d');
  const COLORS = ['#6366f1','#f59e0b','#10b981','#ef4444'];

  function renderDonut(labels, data) {
    if (!ctx) return;
    donut?.destroy();
    donut = new Chart(ctx, {
      type: 'doughnut',
      data: { labels, datasets: [{ data, backgroundColor: COLORS, borderWidth: 0, cutout: '70%' }] },
      options: {
        plugins: { legend: { display: false } },
        responsive: true,
        maintainAspectRatio: true,
        layout:{padding:10}
      }
    });
    const legend = $('#donutLegend');
    if (legend) legend.innerHTML = labels.map((l,i)=>
      `<div class="legend-row"><span class="legend-dot" style="background:${COLORS[i]}"></span><span>${l}</span><strong style="margin-left:auto">${data[i]}%</strong></div>`
    ).join('');
  }

  async function loadPerformance() {
    try{
      const res = await fetch('/api/student-performance/', { headers: { 'X-Requested-With':'XMLHttpRequest' }});
      const j = await res.json();
      renderDonut(j.labels, j.percentages);
    }catch{
      renderDonut(['Excellent','Good','Average','Poor'], [35, 40, 20, 5]);
    }
  }
  async function loadContribution() {
    try{
      const res = await fetch('/api/event-contribution-summary/', { headers: { 'X-Requested-With':'XMLHttpRequest' }});
      const j = await res.json();
      renderDonut(j.labels, j.percentages);
    }catch{
      renderDonut(['Organized','Participated','Reviewed','Other'], [45, 35, 15, 5]);
    }
  }

  $$('.seg-btn').forEach(b => b.addEventListener('click', e => {
    $$('.seg-btn').forEach(x => x.classList.remove('active'));
    e.currentTarget.classList.add('active');
    currentView = e.currentTarget.dataset.view;
    const title = $('#perfTitle');
    if (title) title.textContent = currentView === 'performance' ? 'Student Performance' : 'Event Contribution';
    (currentView === 'performance' ? loadPerformance() : loadContribution()).then(syncHeights);
  }));

  // Calendar
  let calRef = new Date();
  const fmt2 = v => String(v).padStart(2,'0');
  const isSame = (a,b)=>a.getFullYear()==b.getFullYear()&&a.getMonth()==b.getMonth()&&a.getDate()==b.getDate();

  function buildCalendar() {
    const headTitle = $('#calTitle');
    const grid = $('#calGrid');
    if(!grid || !headTitle) return;

    headTitle.textContent = calRef.toLocaleString(undefined,{month:'long', year:'numeric'});

    const first = new Date(calRef.getFullYear(), calRef.getMonth(), 1);
    const last  = new Date(calRef.getFullYear(), calRef.getMonth()+1, 0);
    const startIdx = first.getDay();
    const prevLast = new Date(calRef.getFullYear(), calRef.getMonth(), 0).getDate();

    const cells = [];
    for(let i=startIdx-1;i>=0;i--){ cells.push({text: prevLast - i, date:null, muted:true}); }
    for(let d=1; d<=last.getDate(); d++){
      const dt = new Date(calRef.getFullYear(), calRef.getMonth(), d);
      cells.push({text:d, date:dt, muted:false});
    }
    while(cells.length % 7 !== 0){ cells.push({text: cells.length%7+1, date:null, muted:true}); }

    grid.innerHTML = cells.map(c=>{
      const today = c.date && isSame(c.date, new Date());
      const iso = c.date ? `${c.date.getFullYear()}-${fmt2(c.date.getMonth()+1)}-${fmt2(c.date.getDate())}` : '';
      return `<div class="day${c.muted?' muted':''}${today?' today':''}" data-date="${iso}">${c.text}</div>`;
    }).join('');

    grid.querySelectorAll('.day[data-date]').forEach(el=>{
      el.addEventListener('click', ()=> openDay(new Date(el.dataset.date)));
    });
  }

  function openDay(day){
    const yyyy = day.getFullYear(), mm = String(day.getMonth()+1).padStart(2,'0'), dd = String(day.getDate()).padStart(2,'0');
    const dateStr = `${yyyy}-${mm}-${dd}`;
    const list = $('#upcomingWrap'); if (!list) return;
    const items = (window.DASHBOARD_EVENTS||[]).filter(e => e.date === dateStr);
    list.innerHTML = items.length
      ? items.map(e => `<div class="u-item"><div>${e.title}</div><a class="chip-btn" href="/proposal/${e.id}/detail/"><i class="fa-regular fa-eye"></i> View</a></div>`).join('')
      : `<div class="empty">No events for ${day.toLocaleDateString()}</div>`;
  }

  $('#calPrev')?.addEventListener('click', ()=>{ calRef = new Date(calRef.getFullYear(), calRef.getMonth()-1, 1); buildCalendar(); syncHeights(); });
  $('#calNext')?.addEventListener('click', ()=>{ calRef = new Date(calRef.getFullYear(), calRef.getMonth()+1, 1); buildCalendar(); syncHeights(); });

  // Add event scope passthrough
  $('#addEventBtn')?.addEventListener('click', (e) => {
    const scope = $('#visibilitySelect')?.value || 'all';
    e.currentTarget.href = `/suite/submit/?via=dashboard&scope=${encodeURIComponent(scope)}`;
  });

  // Heatmap
  // Heatmap (fills card)
function renderHeatmap(){
  const wrap = $('#heatmapContainer'); if (!wrap) return;
  const cols = 53, rows = 7;
  const grid = document.createElement('div'); grid.className='hm-grid';
  for (let c=0;c<cols;c++){
    const col = document.createElement('div'); col.className='hm-col';
    for (let r=0;r<rows;r++){
      const cell = document.createElement('div'); cell.className='hm-cell';
      const v = Math.random();
      if (v>0.8) cell.classList.add('l4'); else if (v>0.6) cell.classList.add('l3'); else if (v>0.35) cell.classList.add('l2'); else if (v>0.18) cell.classList.add('l1');
      col.appendChild(cell);
    }
    grid.appendChild(col);
  }
  wrap.innerHTML=''; wrap.appendChild(grid);
  fitHeatmap();
}

function fitHeatmap(){
  const wrap = $('#heatmapContainer'); if(!wrap) return;
  const cols = 53, rows = 7, gap = 3;
  const cs = getComputedStyle(wrap);
  const availW = wrap.clientWidth  - (parseFloat(cs.paddingLeft)||0) - (parseFloat(cs.paddingRight)||0);
  const availH = wrap.clientHeight - (parseFloat(cs.paddingTop)||0)  - (parseFloat(cs.paddingBottom)||0);
  const size = Math.max(4, Math.floor(Math.min(
    (availW - (cols - 1) * gap) / cols,
    (availH - (rows - 1) * gap) / rows
  )));
  wrap.style.setProperty('--hm-size', size + 'px');
  wrap.style.setProperty('--hm-gap',  gap  + 'px');
}


  // To-do (local only)
  const todoKey = 'ems.todo';
  function loadTodos(){
    const list = $('#todoList'); if(!list) return;
    const data = JSON.parse(localStorage.getItem(todoKey)||'[]');
    list.innerHTML = data.map((t,i)=>`
      <li data-i="${i}">
        <input type="checkbox" ${t.done?'checked':''}>
        <span>${t.text}</span>
        <button class="rm" title="Remove"><i class="fa-regular fa-trash-can"></i></button>
      </li>`).join('');

    list.querySelectorAll('input[type="checkbox"]').forEach(cb=>{
      cb.addEventListener('change',e=>{
        const i = +e.target.closest('li').dataset.i;
        data[i].done = e.target.checked;
        localStorage.setItem(todoKey, JSON.stringify(data));
      });
    });

    list.querySelectorAll('.rm').forEach(btn=>{
      btn.addEventListener('click',e=>{
        const i = +e.currentTarget.closest('li').dataset.i;
        data.splice(i,1);
        localStorage.setItem(todoKey, JSON.stringify(data));
        loadTodos();
        syncHeights();
      });
    });
  }

  $('#addTodo')?.addEventListener('click',()=>{
    const text = prompt('New to-do'); if(!text) return;
    const data = JSON.parse(localStorage.getItem(todoKey)||'[]');
    data.unshift({text,done:false});
    localStorage.setItem(todoKey, JSON.stringify(data));
    loadTodos();
    syncHeights();
  });

  function syncHeights(){
    const isDesktop = window.innerWidth > 1200;
    const root = document.documentElement;
    const perf = $('#cardPerformance');
    const acts = $('#cardActions');
    const cal  = $('#cardCalendar');
    const todo = $('#cardTodo');
    const todoList = $('#todoList');
    const todoHeader = $('#cardTodo .card-header');
    const contrib = $('#cardContribution');
  
    if(!isDesktop){
      ['--calH','--contribH','--todoBodyH'].forEach(v=>root.style.removeProperty(v));
      [perf, acts, cal, todo].forEach(el=>{ if(el){ el.style.height=''; el.style.minHeight=''; }});
      if(todoList){ todoList.style.height=''; todoList.style.overflowY=''; }
      return;
    }
  
    // 1) Match Actions + Performance exactly to Calendar height
    if (cal) {
      const calH = Math.ceil(cal.getBoundingClientRect().height);
      root.style.setProperty('--calH', calH + 'px');
      cal.style.height  = calH + 'px';
      if (acts) acts.style.height = calH + 'px';
      if (perf) perf.style.height = calH + 'px';
    }
  
    // 2) To‑do equals Contribution; body scrolls
    if (contrib && todo && todoHeader && todoList) {
      const contribH = Math.ceil(contrib.getBoundingClientRect().height);
      root.style.setProperty('--contribH', contribH + 'px');
      todo.style.height = contribH + 'px';
  
      const cs = getComputedStyle(todo);
      const padV = (parseFloat(cs.paddingTop)||0)+(parseFloat(cs.paddingBottom)||0);
      const borderV = (parseFloat(cs.borderTopWidth)||0)+(parseFloat(cs.borderBottomWidth)||0);
      const headerH = Math.ceil(todoHeader.getBoundingClientRect().height);
      const bodyH = Math.max(0, contribH - headerH - padV - borderV);
  
      root.style.setProperty('--todoBodyH', bodyH + 'px');
      todoList.style.height = bodyH + 'px';
      todoList.style.overflowY = 'auto';
    }
    fitHeatmap();
  }  

  const debounce = (fn,ms=120)=>{ let t; return (...a)=>{ clearTimeout(t); t=setTimeout(()=>fn(...a),ms); }; };

  // Boot
  document.addEventListener('DOMContentLoaded', () => {
    loadPerformance();
    buildCalendar(); openDay(new Date());
    renderHeatmap();
    loadTodos();
    requestAnimationFrame(()=>{ syncHeights(); });
  });

  window.addEventListener('load', ()=>syncHeights());
  window.addEventListener('resize', debounce(syncHeights, 150));
})();
