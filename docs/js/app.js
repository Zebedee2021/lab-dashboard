/**
 * 通用 UI 工具函数
 */
const UI = (() => {
  function statusBadge(level, text) {
    const colors = {
      red: 'bg-red-100 text-red-800 border-red-200',
      yellow: 'bg-yellow-100 text-yellow-800 border-yellow-200',
      green: 'bg-green-100 text-green-800 border-green-200',
      gray: 'bg-gray-100 text-gray-600 border-gray-200',
    };
    const dots = { red: 'bg-red-500', yellow: 'bg-yellow-500', green: 'bg-green-500', gray: 'bg-gray-400' };
    const cls = colors[level] || colors.gray;
    const dot = dots[level] || dots.gray;
    return `<span class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium border ${cls}">
      <span class="w-1.5 h-1.5 rounded-full ${dot}"></span>${text || level}
    </span>`;
  }

  function formatDate(dateStr) {
    if (!dateStr) return '-';
    return dateStr;
  }

  function initNav(activePage) {
    const nav = document.getElementById('main-nav');
    if (!nav) return;
    const pages = [
      { id: 'dashboard', label: '项目看板', icon: 'M4 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2V6zm10 0a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2V6zM4 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2v-2zm10 0a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2v-2z' },
      { id: 'person', label: '人员周报', icon: 'M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197m13.5-9a2.25 2.25 0 11-4.5 0 2.25 2.25 0 014.5 0z' },
      { id: 'risks', label: '风险追踪', icon: 'M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z' },
      { id: 'feedback', label: '反馈记录', icon: 'M7.5 8.25h9m-9 3H12m-9.75 1.51c0 1.6 1.123 2.994 2.707 3.227 1.087.16 2.185.283 3.293.369V21l4.076-4.076a1.526 1.526 0 011.037-.443 48.3 48.3 0 005.128-.484c1.584-.233 2.707-1.626 2.707-3.228V6.741c0-1.602-1.123-2.995-2.707-3.228A48.4 48.4 0 0012 3c-2.392 0-4.744.175-7.043.513C3.373 3.746 2.25 5.14 2.25 6.741v6.018z' },
    ];
    nav.innerHTML = pages.map(p => {
      const active = p.id === activePage;
      const cls = active
        ? 'bg-blue-50 text-blue-700 border-blue-200'
        : 'text-gray-600 hover:bg-gray-50 hover:text-gray-900 border-transparent';
      return `<a href="${p.id}.html" class="flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium border transition-colors ${cls}">
        <svg class="w-5 h-5 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" d="${p.icon}"/></svg>
        ${p.label}
      </a>`;
    }).join('');
  }

  function pageShell(title, activePage) {
    return `
    <div class="min-h-screen bg-gray-50">
      <header class="bg-white border-b border-gray-200 sticky top-0 z-30">
        <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex items-center justify-between h-14">
          <div class="flex items-center gap-3">
            <span class="text-lg font-bold text-gray-900">810 Lab Dashboard</span>
          </div>
          <button onclick="Auth.logout()" class="text-sm text-gray-500 hover:text-gray-700">退出登录</button>
        </div>
      </header>
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
        <div class="flex gap-6">
          <nav id="main-nav" class="w-48 flex-shrink-0 space-y-1 hidden md:block"></nav>
          <main id="app-content" class="flex-1 min-w-0">
            <div class="flex items-center justify-center py-20">
              <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
              <span class="ml-3 text-gray-500">加载中...</span>
            </div>
          </main>
        </div>
      </div>
    </div>`;
  }

  return { statusBadge, formatDate, initNav, pageShell };
})();
