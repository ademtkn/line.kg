(function () {
    'use strict';
    var root = document.documentElement;
    function openDialog(dialog) {
        if (typeof dialog.showModal === 'function') { dialog.showModal(); } else { dialog.setAttribute('open', ''); }
        root.classList.add('partner-scroll-lock');
    }
    function closeDialog(dialog) {
        if (typeof dialog.close === 'function') { dialog.close(); } else { dialog.removeAttribute('open'); }
        root.classList.remove('partner-scroll-lock');
    }
    document.querySelectorAll('[data-partner-open]').forEach(function (button) {
        var dialog = document.getElementById(button.getAttribute('data-partner-open'));
        if (!dialog) { return; }
        button.addEventListener('click', function () { openDialog(dialog); });
        // Esc closes natively; the close button and backdrop clicks are handled here.
        dialog.addEventListener('close', function () { root.classList.remove('partner-scroll-lock'); });
        dialog.addEventListener('click', function (event) {
            if (event.target === dialog || event.target.closest('[data-partner-close]')) { closeDialog(dialog); }
        });
    });
})();
