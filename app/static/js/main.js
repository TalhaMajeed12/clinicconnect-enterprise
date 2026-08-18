(() => {
    'use strict';

    const originalLabels = new WeakMap();
    const closeAlert = (item) => {
        if (!item?.isConnected) return;
        if (window.bootstrap && item.classList.contains('alert-dismissible')) {
            bootstrap.Alert.getOrCreateInstance(item).close();
            return;
        }
        item.classList.remove('show');
        window.setTimeout(() => item.remove(), 180);
    };

    const scheduleAlertDismissal = (item) => {
        if (item.dataset.persist !== undefined) return;
        const isImportant = item.classList.contains('alert-danger') || item.classList.contains('alert-warning');
        const delay = isImportant ? 7000 : 4500;
        let timer = window.setTimeout(() => closeAlert(item), delay);
        const pause = () => window.clearTimeout(timer);
        const resume = () => {
            window.clearTimeout(timer);
            timer = window.setTimeout(() => closeAlert(item), delay);
        };
        item.addEventListener('mouseenter', pause);
        item.addEventListener('mouseleave', resume);
        item.addEventListener('focusin', pause);
        item.addEventListener('focusout', resume);
    };

    document.querySelectorAll('.alert.show').forEach(scheduleAlertDismissal);

    window.showFeedback = (message, type = 'info') => {
        let region = document.getElementById('global-feedback');
        if (!region) {
            region = document.createElement('div');
            region.id = 'global-feedback';
            region.className = 'global-feedback';
            region.setAttribute('aria-live', 'polite');
            document.body.appendChild(region);
        }
        const item = document.createElement('div');
        item.className = `alert alert-${type} fade show shadow-sm mb-2`;
        item.textContent = message;
        region.appendChild(item);
        scheduleAlertDismissal(item);
    };

    const unlockForms = () => {
        document.querySelectorAll('form[data-submitting="true"]').forEach((form) => {
            form.dataset.submitting = 'false';
            form.querySelectorAll('button[type="submit"], input[type="submit"]').forEach((control) => {
                control.disabled = false;
                control.removeAttribute('aria-busy');
                if (control.tagName === 'BUTTON' && originalLabels.has(control)) {
                    control.innerHTML = originalLabels.get(control);
                }
            });
        });
    };

    document.querySelectorAll('form').forEach((form) => {
        if ((form.method || 'get').toLowerCase() !== 'post' || form.dataset.noSubmitLock !== undefined) return;
        form.addEventListener('submit', (event) => {
            if (form.dataset.confirm && !window.confirm(form.dataset.confirm)) {
                event.preventDefault();
                return;
            }
            if (form.dataset.submitting === 'true') {
                event.preventDefault();
                return;
            }
            form.dataset.submitting = 'true';
            const submitter = event.submitter || form.querySelector('button[type="submit"], input[type="submit"]');
            if (!submitter) return;
            submitter.disabled = true;
            submitter.setAttribute('aria-busy', 'true');
            if (submitter.tagName === 'BUTTON') {
                originalLabels.set(submitter, submitter.innerHTML);
                submitter.innerHTML = '<span class="spinner-border spinner-border-sm me-2" aria-hidden="true"></span>Working…';
            }
        });
    });

    document.querySelectorAll('a[href^="#"]:not([href="#"])').forEach((link) => {
        link.addEventListener('click', (event) => {
            const target = document.querySelector(link.getAttribute('href'));
            if (!target) return;
            event.preventDefault();
            target.scrollIntoView({behavior: 'smooth', block: 'start'});
            window.history.replaceState(null, '', link.getAttribute('href'));
            window.setTimeout(() => target.focus({preventScroll: true}), 400);
        });
    });

    document.querySelectorAll('.navbar .nav-link:not(.dropdown-toggle)').forEach((link) => {
        link.addEventListener('click', () => {
            const menu = document.getElementById('navbarNav');
            if (menu?.classList.contains('show') && window.bootstrap) {
                bootstrap.Collapse.getOrCreateInstance(menu).hide();
            }
        });
    });

    document.querySelectorAll('.nav-link.active').forEach((link) => link.setAttribute('aria-current', 'page'));

    window.addEventListener('pageshow', unlockForms);
})();
