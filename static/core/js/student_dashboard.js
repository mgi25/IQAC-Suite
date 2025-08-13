/* Student Dashboard – frontend only */
(function () {
    const $  = (s, r=document)=>r.querySelector(s);
    const $$ = (s, r=document)=>Array.from(r.querySelectorAll(s));
  
    // KPI clicks (student tabs/routes)
    $('#kpiEvents')?.addEventListener('click', ()=> location.hash = '#events&type=participated');
    $('#kpiAchievements')?.addEventListener('click', ()=> location.hash = '#achievements');
    $('#kpiClubs')?.addEventListener('click', ()=> location.hash = '#profile&tab=clubs');
    $('#kpiActivityScore')?.addEventListener('click', ()=> location.hash = '#profile&tab=score');
  
    // Donut
    let donut;
    const ctx = $('#donutChart')?.getContext('2d');
    const COLORS = ['#6366f1','#0ea5e9','#10b981','#f59e0b'];
  
    function renderDonut(labels, data) {
      if (!ctx) return;
      donut?.destroy();
      donut = new Chart(ctx, {
        type: 'doughnut',
        data: { labels, datasets: [{ data, backgroundColor: COLORS, borderWidth: 0, cutout: '70%' }] },
        options: { plugins: { legend: { display:false } }, responsive:true, maintainAspectRatio:true, layout:{padding:10} }
      });
      const legend = $('#donutLegend');
      if (legend) legend.innerHTML = labels.map((l,i)=>
        `<div class="legend-row"><span class="legend-dot" style="background:${COLORS[i]}"></span><span>${l}</span><strong style="margin-left:auto">${data[i]}%</strong></div>`
      ).join('');
    }
  
    async function loadPerformance(){
      try{
        const res = await fetch('/api/student/graduate-attributes/', { headers:{'X-Requested-With':'XMLHttpRequest'} });
        const j = await res.json();                 // {labels:[], percentages:[]}
        renderDonut(j.labels, j.percentages);
      }catch{
        renderDonut(['Critical Thinking','Leadership','Communication','Teamwork'], [30,30,25,15]);
      }
    }
  
    async function loadContribution(){
      try{
        const res = await fetch('/api/student/contribution-summary/', { headers:{'X-Requested-With':'XMLHttpRequest'} });
        const j = await res.json();                 // {labels:[], percentages:[]}
        renderDonut(j.labels, j.percentages);
      }catch{
        renderDonut(['Events','Roles','Leadership','Other'], [55,25,15,5]);
      }
    }
  
    $$('.seg-btn').forEach(b=>b.addEventListener('click',e=>{
      $$('.seg-btn').forEach(x=>x.classList.remove('active'));
      e.currentTarget.classList.add('active');
      const v = e.currentTarget.dataset.view;
      $('#perfTitle').textContent = v==='performance' ? 'Graduate Attributes' : 'Contribution';
      (v==='performance'? loadPerformance(): loadContribution()).then(syncHeights);
    }));
  
    // Calendar
    let calRef = new Date();
    const fmt2 = v => String(v).padStart(2,'0');
    const isSame = (a,b)=>a.getFullYear()==b.getFullYear()&&a.getMonth()==b.getMonth()&&a.getDate()==b.getDate();
  
    function buildCalendar(){
      const headTitle = $('#calTitle'), grid = $('#calGrid');
      if(!grid||!headTitle) return;
      headTitle.textContent = calRef.toLocaleString(undefined,{month:'long', year:'numeric'});
  
      const first = new Date(calRef.getFullYear(), calRef.getMonth(), 1);
      const last  = new Date(calRef.getFullYear(), calRef.getMonth()+1, 0);
      const startIdx = first.getDay();
      const prevLast = new Date(calRef.getFullYear(), calRef.getMonth(), 0).getDate();
  
      const cells=[];
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
      const yyyy=day.getFullYear(), mm=String(day.getMonth()+1).padStart(2,'0'), dd=String(day.getDate()).padStart(2,'0');
      const dateStr = `${yyyy}-${mm}-${dd}`;
      const list = $('#upcomingWrap'); if(!list) return;
      const items = (window.DASHBOARD_EVENTS||[]).filter(e => e.date === dateStr);
      list.innerHTML = items.length
        ? items.map(e => `<div class="u-item"><div>${e.title}</div><a class="chip-btn" href="/proposal/${e.id}/detail/"><i class="fa-regular fa-eye"></i> View</a></div>`).join('')
        : `<div class="empty">No events for ${day.toLocaleDateString()}</div>`;
    }
  
    $('#calPrev')?.addEventListener('click', ()=>{ calRef = new Date(calRef.getFullYear(), calRef.getMonth()-1, 1); buildCalendar(); syncHeights(); });
    $('#calNext')?.addEventListener('click', ()=>{ calRef = new Date(calRef.getFullYear(), calRef.getMonth()+1, 1); buildCalendar(); syncHeights(); });
  
    // Heatmap
    function renderHeatmap(){
      const wrap = $('#heatmapContainer'); if(!wrap) return;
      const cols=53, rows=7, grid=document.createElement('div'); grid.className='hm-grid';
      for(let c=0;c<cols;c++){
        const col=document.createElement('div'); col.className='hm-col';
        for(let r=0;r<rows;r++){
          const cell=document.createElement('div'); cell.className='hm-cell';
          const v=Math.random(); if(v>0.8)cell.classList.add('l4'); else if(v>0.6)cell.classList.add('l3'); else if(v>0.35)cell.classList.add('l2'); else if(v>0.18)cell.classList.add('l1');
          col.appendChild(cell);
        }
        grid.appendChild(col);
      }
      wrap.innerHTML=''; wrap.appendChild(grid);
      fitHeatmap();
    }
    function fitHeatmap(){
      const wrap = $('#heatmapContainer'); if(!wrap) return;
      const cols=53, rows=7, gap=3;
      const cs=getComputedStyle(wrap);
      const availW=wrap.clientWidth-(parseFloat(cs.paddingLeft)||0)-(parseFloat(cs.paddingRight)||0);
      const availH=wrap.clientHeight-(parseFloat(cs.paddingTop)||0)-(parseFloat(cs.paddingBottom)||0);
      const size=Math.max(4, Math.floor(Math.min(
        (availW - (cols-1)*gap)/cols,
        (availH - (rows-1)*gap)/rows
      )));
      wrap.style.setProperty('--hm-size', size+'px');
      wrap.style.setProperty('--hm-gap', gap+'px');
    }
  
    // Simple local proposals list enhancer (optional)
    // (kept minimal to match teacher parity)
  
    // Height sync
    function syncHeights(){
      const isDesktop = window.innerWidth > 1200;
      const root=document.documentElement;
      const perf=$('#cardPerformance'), acts=$('#cardActions'), cal=$('#cardCalendar');
      const todo=$('#cardTodo'), todoList=$('#todoList'), todoHeader=$('#cardTodo .card-header');
      const contrib=$('#cardContribution');
  
      if(!isDesktop){
        ['--calH','--contribH','--todoBodyH'].forEach(v=>root.style.removeProperty(v));
        [perf,acts,cal,todo].forEach(el=>{ if(el){ el.style.height=''; el.style.minHeight=''; }});
        if(todoList){ todoList.style.height=''; todoList.style.overflowY=''; }
        return;
      }
  
      if (cal){
        const calH=Math.ceil(cal.getBoundingClientRect().height);
        root.style.setProperty('--calH', calH+'px');
        cal.style.height=calH+'px';
        if(acts) acts.style.height=calH+'px';
        if(perf) perf.style.height=calH+'px';
      }
  
      if (contrib && todo && todoHeader && todoList){
        const contribH=Math.ceil(contrib.getBoundingClientRect().height);
        root.style.setProperty('--contribH', contribH+'px');
        todo.style.height=contribH+'px';
        const cs=getComputedStyle(todo);
        const padV=(parseFloat(cs.paddingTop)||0)+(parseFloat(cs.paddingBottom)||0);
        const borderV=(parseFloat(cs.borderTopWidth)||0)+(parseFloat(cs.borderBottomWidth)||0);
        const headerH=Math.ceil(todoHeader.getBoundingClientRect().height);
        const bodyH=Math.max(0, contribH - headerH - padV - borderV);
        root.style.setProperty('--todoBodyH', bodyH+'px');
        todoList.style.height=bodyH+'px';
        todoList.style.overflowY='auto';
      }
      fitHeatmap();
    }
  
    const debounce=(fn,ms=120)=>{let t;return(...a)=>{clearTimeout(t);t=setTimeout(()=>fn(...a),ms);}};
  
    document.addEventListener('DOMContentLoaded', ()=>{
      loadPerformance();
      buildCalendar(); openDay(new Date());
      renderHeatmap();
      requestAnimationFrame(()=>{ syncHeights(); });
    });
    window.addEventListener('load', ()=>syncHeights());
    window.addEventListener('resize', debounce(syncHeights,150));
  })();
  