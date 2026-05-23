// ═══════════════════════════════════════════════════════════════════════════
// TEEN BOT DASHBOARD — Core JavaScript
// ═══════════════════════════════════════════════════════════════════════════

// ─── Sidebar ───────────────────────────────────────────────────────────────

function toggleSidebar() {
    document.getElementById('sidebar').classList.toggle('open');
}

// Close sidebar on outside click (mobile)
document.addEventListener('click', function(e) {
    const sidebar = document.getElementById('sidebar');
    const toggle = document.querySelector('.navbar-toggle');
    if (window.innerWidth <= 992 && sidebar && sidebar.classList.contains('open')) {
        if (!sidebar.contains(e.target) && toggle && !toggle.contains(e.target)) {
            sidebar.classList.remove('open');
        }
    }
});

// ─── Server Selector Dropdown ──────────────────────────────────────────────

function toggleServerDropdown() {
    const dd = document.getElementById('serverDropdown');
    const sel = document.getElementById('serverSelector');
    if (dd) {
        dd.classList.toggle('show');
        if (sel) sel.classList.toggle('open');
    }
}

document.addEventListener('click', function(e) {
    const sel = document.getElementById('serverSelector');
    if (sel && !sel.contains(e.target)) {
        const dd = document.getElementById('serverDropdown');
        if (dd) dd.classList.remove('show');
        sel.classList.remove('open');
    }
});

// ─── Dropdown ──────────────────────────────────────────────────────────────

function toggleDropdown(btn) {
    const menu = btn.nextElementSibling;
    if (menu) menu.classList.toggle('show');
}

document.addEventListener('click', function(e) {
    document.querySelectorAll('.dropdown-menu-custom.show').forEach(menu => {
        if (!menu.parentElement.contains(e.target)) {
            menu.classList.remove('show');
        }
    });
});

// ─── Modal ─────────────────────────────────────────────────────────────────

function openModal(title, bodyHTML, footerHTML) {
    const overlay = document.getElementById('modalOverlay');
    const titleEl = document.getElementById('modalTitle');
    const bodyEl = document.getElementById('modalBody');
    const footerEl = document.getElementById('modalFooter');
    if (titleEl) titleEl.innerHTML = title;
    if (bodyEl) bodyEl.innerHTML = bodyHTML;
    if (footerEl) footerEl.innerHTML = footerHTML || '';
    if (overlay) overlay.classList.add('show');
    document.body.style.overflow = 'hidden';
}

function closeModal() {
    const overlay = document.getElementById('modalOverlay');
    if (overlay) overlay.classList.remove('show');
    document.body.style.overflow = '';
}

document.addEventListener('keydown', function(e) {
    if (e.key === 'Escape') closeModal();
});

// ─── Toast Notifications ────────────────────────────────────────────────────

function showToast(icon, message, type) {
    type = type || 'info';
    const container = document.getElementById('toastContainer');
    if (!container) return;

    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.innerHTML = `
        <div class="toast-icon">${icon}</div>
        <div class="toast-body">${message}</div>
        <button class="toast-close" onclick="this.parentElement.remove()"><i class="bi bi-x"></i></button>
    `;
    container.appendChild(toast);

    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transform = 'translateX(100px)';
        toast.style.transition = 'all 0.3s ease-out';
        setTimeout(() => toast.remove(), 300);
    }, 4000);
}

// ─── Search ────────────────────────────────────────────────────────────────

function handleSearch(query) {
    if (query.length < 2) return;
    const sidebarLinks = document.querySelectorAll('.sidebar-link');
    const q = query.toLowerCase();
    sidebarLinks.forEach(link => {
        const text = link.textContent.toLowerCase();
        link.style.display = text.includes(q) ? 'flex' : 'none';
    });
    // Show section labels only if they have visible children
    document.querySelectorAll('.sidebar-section-label').forEach(label => {
        const next = label.nextElementSibling;
        let hasVisible = false;
        let el = next;
        while (el && el.classList.contains('sidebar-link')) {
            if (el.style.display !== 'none') { hasVisible = true; break; }
            el = el.nextElementSibling;
        }
        label.style.display = hasVisible ? 'block' : 'none';
    });
}

// ─── Active Nav Highlight ──────────────────────────────────────────────────

document.addEventListener('DOMContentLoaded', function() {
    const currentPath = window.location.pathname;
    document.querySelectorAll('.sidebar-link').forEach(link => {
        const href = link.getAttribute('href');
        if (href && currentPath.startsWith(href) && href !== '/dashboard') {
            link.classList.add('active');
        }
    });

    // Init toggles
    document.querySelectorAll('.form-toggle').forEach(toggle => {
        toggle.addEventListener('click', function() {
            this.classList.toggle('active');
        });
    });
});

// ─── Clipboard Copy ────────────────────────────────────────────────────────

function copyToClipboard(text) {
    navigator.clipboard.writeText(text).then(() => {
        showToast('✅', 'Copiado al portapapeles', 'success');
    });
}

// ─── Format Number ─────────────────────────────────────────────────────────

function formatNumber(num) {
    return num ? num.toLocaleString() : '0';
}

// ─── Time Ago ──────────────────────────────────────────────────────────────

function timeAgo(timestamp) {
    const now = Date.now();
    const diff = now - (timestamp * 1000);
    const seconds = Math.floor(diff / 1000);
    const minutes = Math.floor(seconds / 60);
    const hours = Math.floor(minutes / 60);
    const days = Math.floor(hours / 24);

    if (days > 0) return `hace ${days}d`;
    if (hours > 0) return `hace ${hours}h`;
    if (minutes > 0) return `hace ${minutes}m`;
    return `hace ${seconds}s`;
}

// ─── Confirm Dialog ────────────────────────────────────────────────────────

function confirmAction(message, callback) {
    openModal(
        '<i class="bi bi-exclamation-triangle" style="color: var(--yellow);"></i> Confirmar',
        `<p>${message}</p>`,
        `<button class="btn-ghost" onclick="closeModal()">Cancelar</button>
         <button class="btn-danger" onclick="closeModal(); (${callback.toString()})()">Confirmar</button>`
    );
}
