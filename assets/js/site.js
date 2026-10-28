(function () {
    'use strict';
    document.querySelectorAll('.accordion').forEach(function (accordion) {
        var buttons = Array.from(accordion.querySelectorAll('button[aria-controls]'));
        function setExpanded(button, expanded) {
            var panel = document.getElementById(button.getAttribute('aria-controls'));
            if (!panel) { return; }
            button.setAttribute('aria-expanded', String(expanded));
            panel.classList.toggle('show', expanded);
        }
        buttons.forEach(function (button, index) {
            button.addEventListener('click', function () {
                var expanded = button.getAttribute('aria-expanded') !== 'true';
                buttons.forEach(function (other) { setExpanded(other, other === button && expanded); });
            });
            button.addEventListener('keydown', function (event) {
                var next;
                if (event.key === 'ArrowDown') { next = (index + 1) % buttons.length; }
                if (event.key === 'ArrowUp') { next = (index + buttons.length - 1) % buttons.length; }
                if (event.key === 'Home') { next = 0; }
                if (event.key === 'End') { next = buttons.length - 1; }
                if (next !== undefined) { event.preventDefault(); buttons[next].focus(); }
            });
        });
    });
    document.querySelectorAll('.skip-link').forEach(function (link) {
        link.addEventListener('click', function () {
            var target = document.getElementById('main-content');
            if (target) { target.focus({ preventScroll: true }); }
        });
    });
})();
