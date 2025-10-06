/* Student Dashboard – frontend only */
(function () {
    const $  = (s, r=document)=>r.querySelector(s);
    const $$ = (s, r=document)=>Array.from(r.querySelectorAll(s));
  
    // KPI clicks (student tabs/routes)
    $('#kpiEvents')?.addEventListener('click', ()=> location.hash = '#events&type=participated');
    $('#kpiAchievements')?.addEventListener('click', ()=> location.hash = '#achievements');
    $('#kpiClubs')?.addEventListener('click', ()=> location.hash = '#profile&tab=clubs');
    $('#kpiActivityScore')?.addEventListener('click', ()=> location.hash = '#profile&tab=score');

    // Performance/Contribution tab switching
    document.addEventListener('click', (e) => {
      if (e.target.matches('[data-view="performance"]')) {
        e.preventDefault();
        document.querySelectorAll('[data-view]').forEach(btn => btn.classList.remove('active'));
        e.target.classList.add('active');
        $('#perfTitle').textContent = 'Performance Analytics';
        loadPerformance();
      } else if (e.target.matches('[data-view="contribution"]')) {
        e.preventDefault();
        document.querySelectorAll('[data-view]').forEach(btn => btn.classList.remove('active'));
        e.target.classList.add('active');
        $('#perfTitle').textContent = 'Event Contributions';
        loadContribution();
      }
    });
  
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
      if (legend) legend.innerHTML = labels.map((l,i)=>{
        const val = typeof data[i] === 'number' ? Math.round(data[i]*10)/10 : data[i];
        return `<div class="legend-row"><span class="legend-dot" style="background:${COLORS[i]}"></span><span>${l}</span><strong style="margin-left:auto">${val}%</strong></div>`;
      }).join('');
    }
  
    async function loadPerformance(){
      try{
        const res = await fetch('/api/student/performance-data/', { headers:{'X-Requested-With':'XMLHttpRequest'} });
        const j = await res.json();
        
        // Update performance statistics in the UI if needed
        if (j.total_events !== undefined) {
          // You can update KPI cards here if they exist
          const totalEventsEl = $('#totalEvents');
          if (totalEventsEl) totalEventsEl.textContent = j.total_events;
          
          const participationRateEl = $('#participationRate');
          if (participationRateEl) participationRateEl.textContent = j.participation_rate + '%';
        }
        
        // Use actual participation data for donut chart
        const labels = ['Participated', 'Not Participated'];
        const data = [j.participation_rate, 100 - j.participation_rate];
        renderDonut(labels, data);
      }catch{
        renderDonut(['Critical Thinking','Leadership','Communication','Teamwork'], [30,30,25,15]);
      }
    }

    async function loadRecentActivity() {
      try {
        const res = await fetch('/api/user/events-data/', { headers: {'X-Requested-With': 'XMLHttpRequest'} });
        const j = await res.json();

        const actionsCard = document.querySelector('#cardActions .list');
        if (actionsCard && Array.isArray(j.events)) {
          if (j.events.length > 0) {
            actionsCard.innerHTML = j.events.slice(0, 5).map(event => `
              <article class="list-item">
                <div class="bullet"><i class="fa-solid fa-circle-check"></i></div>
                <div class="list-body">
                  <h4>${event.title}</h4>
                  <p>${event.description || ''} - ${event.created_at || ''}</p>
                  <small>Status: ${event.status || ''}</small>
                </div>
              </article>
            `).join('');
          } else {
            actionsCard.innerHTML = '<div class="empty">No recent activity</div>';
          }
        }
      } catch (ex) {
        console.error('Failed to fetch recent activity', ex);
      }
    }

    // Add event button - now opens modal instead
    $('#addEventBtn')?.addEventListener('click', (e) => {
      e.preventDefault();
      showEventCreationModal();
    });

    // Clear event details
    $('#clearEventDetails')?.addEventListener('click', () => {
      $('#eventDetailsContent').innerHTML = '<div class="empty">Click on an event in the calendar to view details</div>';
      $('#clearEventDetails').style.display = 'none';
    });

    function showEventCreationModal() {
      const modal = $('#eventCreationModal');
      modal.style.display = 'flex';
      
      // Load places
      loadPlaces('#eventVenue');
      
      // Handle form submission
      $('#eventCreationForm').onsubmit = async (e) => {
        e.preventDefault();
        // This would redirect to the actual event creation page
        window.location.href = `/suite/submit/?via=dashboard`;
      };
      
      // Handle close events
      $('#closeEventModal').onclick = () => modal.style.display = 'none';
      $('#cancelEvent').onclick = () => modal.style.display = 'none';
    }

    async function loadPlaces(selector) {
      try {
        const response = await fetch('/api/dashboard/places/', { headers: {'X-Requested-With':'XMLHttpRequest'} });
        const data = await response.json();
        const select = $(selector);
        if (select) {
          select.innerHTML = '<option value="">Select venue...</option>' + 
            data.places.map(p => `<option value="${p.name}">${p.name}</option>`).join('');
        }
      } catch (ex) {
        console.error('Failed to load places:', ex);
      }
    }

  // No visibility dropdown on student; calendar handled by shared CalendarModule
  
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
      const eventDetails=$('#cardEventDetails');
      const contrib=$('#cardContribution');
  
      if(!isDesktop){
        ['--calH','--contribH','--eventDetailsH'].forEach(v=>root.style.removeProperty(v));
        [perf,acts,cal,eventDetails].forEach(el=>{ if(el){ el.style.height=''; el.style.minHeight=''; }});
        return;
      }
  
      if (cal){
        const calH=Math.ceil(cal.getBoundingClientRect().height);
        root.style.setProperty('--calH', calH+'px');
        cal.style.height=calH+'px';
        if(acts) acts.style.height=calH+'px';
        if(perf) perf.style.height=calH+'px';
      }
  
      if (contrib && eventDetails){
        const contribH=Math.ceil(contrib.getBoundingClientRect().height);
        root.style.setProperty('--contribH', contribH+'px');
        eventDetails.style.height=contribH+'px';
      }
      fitHeatmap();
    }
  
    const debounce=(fn,ms=120)=>{let t;return(...a)=>{clearTimeout(t);t=setTimeout(()=>fn(...a),ms);}};
  
    // Tab switching for Performance/Contribution
    document.addEventListener('click', (e) => {
      if (e.target.matches('[data-view]')) {
        const view = e.target.dataset.view;
        const parent = e.target.closest('.card');
        
        // Update active button
        parent.querySelectorAll('.seg-btn').forEach(btn => btn.classList.remove('active'));
        e.target.classList.add('active');
        
        // Update title and load appropriate data
        const title = parent.querySelector('#perfTitle');
        if (view === 'performance') {
          if (title) title.textContent = 'Performance Metrics';
          loadPerformance();
        } else if (view === 'contribution') {
          if (title) title.textContent = 'Yearly Contribution';
          loadContribution();
        }
      }
    });

    document.addEventListener('DOMContentLoaded', ()=>{
      loadPerformance();
      loadRecentActivity();
      // Initialize shared calendar module (uses same endpoint as admin)
      try{
        if (window.CalendarModule && typeof CalendarModule.init === 'function'){
            // Show multi-day events like admin calendar (do not filter to start-only)
            CalendarModule.init({ endpoint: '/api/calendar/?category=all', inlineEventsElementId: 'calendarEventsJson', showOnlyStartDate: false });
          }
      }catch(ex){ console.error('CalendarModule init failed', ex); }
      // Heatmap will be populated by contributions API with event-date aggregation
      // Fallback visual if API fails is handled inside loadContribution
      loadContribution();
      requestAnimationFrame(()=>{ syncHeights(); });
    });
    window.addEventListener('load', ()=>syncHeights());
    window.addEventListener('resize', debounce(syncHeights,150));
  })();
  