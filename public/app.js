// Bulletproof UPSC Dashboard Frontend

let rawData = [];
let currentFilter = 'ALL';

// Safe property accessor
function safeString(val) {
  if (val === null || val === undefined) return '';
  return String(val).trim();
}

function safeArray(val) {
  if (Array.isArray(val)) return val;
  if (val) return [val];
  return [];
}

// Normalize GS Tags
function normalizeTag(tagRaw) {
  let tag = safeString(tagRaw).toUpperCase();
  tag = tag.replace(/GS PAPER\s*/g, 'GS');
  if (/^[1234]$/.test(tag)) tag = 'GS' + tag;
  if (!tag.startsWith('GS')) tag = 'OTHER';
  return tag;
}

// Get Badge Style
function getBadgeClass(tag) {
  if (tag.includes('GS1')) return 'tag-gs1';
  if (tag.includes('GS2')) return 'tag-gs2';
  if (tag.includes('GS3')) return 'tag-gs3';
  if (tag.includes('GS4')) return 'tag-gs4';
  return 'tag-default';
}

// Fetch and render
async function init() {
  lucide.createIcons();
  
  try {
    const res = await fetch('../data/news.json?t=' + Date.now());
    if (!res.ok) throw new Error('Network response was not ok');
    const data = await res.json();
    rawData = safeArray(data);
    
    document.getElementById('article-count').innerText = `${rawData.length} Articles Enriched`;
    renderFeed();
  } catch (err) {
    console.error('Error loading news:', err);
    document.getElementById('feed-container').innerHTML = `
      <div class="glass p-8 rounded-2xl text-center">
        <i data-lucide="alert-circle" class="w-12 h-12 text-red-500 mx-auto mb-4"></i>
        <h3 class="text-xl font-bold text-red-400">Failed to load data</h3>
        <p class="text-zinc-400 mt-2">Make sure the python pipeline has generated data/news.json.</p>
      </div>
    `;
    lucide.createIcons();
  }

  // Setup filters
  document.querySelectorAll('.filter-btn').forEach(btn => {
    btn.addEventListener('click', (e) => {
      currentFilter = btn.dataset.tag;
      
      // Update UI
      document.querySelectorAll('.filter-btn').forEach(b => {
        b.classList.remove('bg-indigo-600/30', 'border', 'border-indigo-500/50');
        b.querySelector('.check-icon').classList.add('hidden');
      });
      btn.classList.add('bg-indigo-600/30', 'border', 'border-indigo-500/50');
      btn.querySelector('.check-icon').classList.remove('hidden');
      
      renderFeed();
    });
  });
  
  // Set ALL as active initially
  const allBtn = document.querySelector('[data-tag="ALL"]');
  allBtn.classList.add('bg-indigo-600/30', 'border', 'border-indigo-500/50');
  allBtn.querySelector('.check-icon').classList.remove('hidden');
}

function renderFeed() {
  const container = document.getElementById('feed-container');
  
  const filtered = rawData.filter(article => {
    if (currentFilter === 'ALL') return true;
    const tags = safeArray(article.gs_tags).map(normalizeTag);
    return tags.includes(currentFilter);
  });

  if (filtered.length === 0) {
    container.innerHTML = `
      <div class="glass p-8 rounded-2xl text-center">
        <i data-lucide="inbox" class="w-12 h-12 text-zinc-500 mx-auto mb-4"></i>
        <h3 class="text-lg font-medium text-zinc-300">No articles found</h3>
        <p class="text-sm text-zinc-500 mt-1">Try changing the filter.</p>
      </div>
    `;
    lucide.createIcons();
    return;
  }

  container.innerHTML = filtered.map((article, idx) => {
    // Safely extract properties
    const title = safeString(article.title) || 'Untitled';
    const source = safeString(article.feed_source) || 'Unknown Source';
    const dateStr = safeString(article.published_date);
    const dateObj = dateStr ? new Date(dateStr) : null;
    const dateFormatted = (dateObj && !isNaN(dateObj)) ? dateObj.toLocaleDateString() : dateStr;
    const url = safeString(article.url) || '#';
    
    // Deep Analysis
    const da = article.deep_analysis || {};
    const summary = safeString(da.what) || safeString(article.summary) || 'No summary available.';
    const why = safeString(da.why);
    const implications = safeString(da.implications);
    const wayForward = safeString(da.way_forward);
    
    // UPSC Layer
    const utl = article.upsc_thinking_layer || {};
    const prelims = safeString(utl.prelims_angle);
    const mains = safeString(utl.mains_angle);

    // Tags
    const tags = safeArray(article.gs_tags).map(normalizeTag);
    const topics = safeArray(article.topics).map(safeString).filter(Boolean);
    
    const allBadges = [...tags, ...topics].slice(0, 4);

    return `
      <div class="glass rounded-2xl p-6 card-hover transition duration-300">
        <div class="flex items-center justify-between mb-3">
          <div class="flex items-center gap-2 text-xs text-zinc-400 font-medium">
            <i data-lucide="rss" class="w-3 h-3"></i>
            <span>${source}</span>
            <span>&bull;</span>
            <span>${dateFormatted}</span>
          </div>
        </div>
        
        <h2 class="text-xl font-bold text-white mb-3 leading-snug">
          <a href="${url}" target="_blank" class="hover:text-indigo-400 transition-colors">${title}</a>
        </h2>
        
        <div class="flex flex-wrap gap-2 mb-4">
          ${allBadges.map(b => `<span class="px-2.5 py-1 rounded-full text-[10px] font-bold tracking-wider ${getBadgeClass(b)}">${b}</span>`).join('')}
        </div>
        
        <p class="text-sm text-zinc-300 leading-relaxed mb-4">${summary}</p>
        
        ${(why || implications || wayForward || prelims || mains) ? `
          <button onclick="toggleExpand('expand-${idx}', this)" class="text-xs font-semibold text-indigo-400 hover:text-indigo-300 flex items-center gap-1 transition-colors">
            <i data-lucide="chevron-down" class="w-4 h-4 transition-transform duration-300"></i>
            <span class="btn-text">View Deep Analysis</span>
          </button>
          
          <div id="expand-${idx}" class="expand-content mt-4 border-t border-zinc-800/50 pt-4 space-y-4">
            
            ${why ? `
              <div class="bg-zinc-900/50 rounded-xl p-4 border border-zinc-800">
                <h4 class="text-xs uppercase tracking-wider text-indigo-400 font-bold flex items-center gap-2 mb-2">
                  <i data-lucide="help-circle" class="w-4 h-4"></i> Why It Matters
                </h4>
                <p class="text-sm text-zinc-300 leading-relaxed">${why}</p>
              </div>
            ` : ''}

            ${implications ? `
              <div class="bg-zinc-900/50 rounded-xl p-4 border border-zinc-800">
                <h4 class="text-xs uppercase tracking-wider text-rose-400 font-bold flex items-center gap-2 mb-2">
                  <i data-lucide="trending-up" class="w-4 h-4"></i> Implications
                </h4>
                <p class="text-sm text-zinc-300 leading-relaxed">${implications}</p>
              </div>
            ` : ''}
            
            ${wayForward ? `
              <div class="bg-zinc-900/50 rounded-xl p-4 border border-zinc-800">
                <h4 class="text-xs uppercase tracking-wider text-emerald-400 font-bold flex items-center gap-2 mb-2">
                  <i data-lucide="arrow-right-circle" class="w-4 h-4"></i> Way Forward
                </h4>
                <p class="text-sm text-zinc-300 leading-relaxed">${wayForward}</p>
              </div>
            ` : ''}

            ${(prelims || mains) ? `
              <div class="mt-6">
                <h3 class="text-sm font-bold text-white mb-3 flex items-center gap-2">
                  <i data-lucide="target" class="w-4 h-4 text-amber-400"></i> UPSC Angles
                </h3>
                <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                  ${prelims ? `
                    <div class="bg-amber-500/10 border border-amber-500/20 rounded-xl p-4">
                      <h4 class="text-xs font-bold text-amber-400 mb-2 uppercase tracking-wide">Prelims Focus</h4>
                      <p class="text-[13px] text-zinc-300 leading-relaxed">${prelims}</p>
                    </div>
                  ` : ''}
                  ${mains ? `
                    <div class="bg-blue-500/10 border border-blue-500/20 rounded-xl p-4">
                      <h4 class="text-xs font-bold text-blue-400 mb-2 uppercase tracking-wide">Mains Blueprint</h4>
                      <p class="text-[13px] text-zinc-300 leading-relaxed">${mains}</p>
                    </div>
                  ` : ''}
                </div>
              </div>
            ` : ''}
            
          </div>
        ` : ''}
      </div>
    `;
  }).join('');
  
  lucide.createIcons();
}

window.toggleExpand = function(id, btn) {
  const content = document.getElementById(id);
  const icon = btn.querySelector('i');
  const text = btn.querySelector('.btn-text');
  
  if (content.classList.contains('open')) {
    content.classList.remove('open');
    icon.style.transform = 'rotate(0deg)';
    text.innerText = 'View Deep Analysis';
  } else {
    content.classList.add('open');
    icon.style.transform = 'rotate(180deg)';
    text.innerText = 'Hide Analysis';
  }
};

document.addEventListener('DOMContentLoaded', init);
