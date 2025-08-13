/* core/js/admin_dashboard.js — smart fallbacks for Export & View All Proposals */
(function(){
    function unique(list){ return [...new Set(list.filter(Boolean))]; }
  
    async function tryNavigate(candidates){
      for (const url of candidates){
        try{
          const res = await fetch(url, { method:'GET', credentials:'same-origin', cache:'no-store' });
          if (res.ok) { window.location.href = url; return true; }
        }catch(_){}
      }
      return false;
    }
  
    function bindSmartLink(el){
      if (!el) return;
      const primary = (el.getAttribute('href')||'').trim();
      const fallbacks = ((el.dataset && el.dataset.try) ? el.dataset.try : '')
        .split(',').map(s=>s.trim());
      const candidates = unique([primary, ...fallbacks].filter(h=>h && h !== '#'));
      if (!candidates.length) return;
  
      el.addEventListener('click', async (e)=>{
        e.preventDefault();
        const ok = await tryNavigate(candidates);
        if (!ok) alert('Destination not found.');
      });
    }
  
    function byId(id){ return document.getElementById(id); }
  
    document.addEventListener('DOMContentLoaded', function(){
      // Export button: support both ids
      bindSmartLink(byId('btnExport'));
      bindSmartLink(byId('exportBtn'));
  
      // View All Proposals: support old id and current class
      bindSmartLink(byId('viewAllProposals'));
      bindSmartLink(document.querySelector('.view-all-link'));
    });
  })();
  
