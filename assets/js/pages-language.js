(function () {
    'use strict';
    // The Pages host cannot send frame-ancestors, so leave any frame we are shown in.
    try { if (window.top !== window.self) { window.top.location.replace(window.self.location.href); } } catch (e) { /* Blocked by the browser. */ }

    // The language switch stores its choice before navigating, so a saved preference never undoes it.
    document.addEventListener('click', function (event) {
        var link = event.target.closest && event.target.closest('[data-language]');
        if (link) { try { localStorage.setItem('linekg.language', link.getAttribute('data-language')); } catch (e) {} }
    });

    var address = new URL(window.location.href);
    var kyrgyzPath = /^\/ky(\/|$)/.test(address.pathname);
    var route = address.pathname.replace(/^\/ky(?=\/|$)/, '').replace(/^\/+/, '').replace(/\.html$/, '').replace(/\/+$/, '');
    if (route === 'index') { route = ''; }
    var selected = address.searchParams.get('lang');
    if (selected !== 'en' && selected !== 'ky') {
        selected = kyrgyzPath ? 'ky' : null;
        if (!selected) { try { selected = localStorage.getItem('linekg.language'); } catch (e) {} }
    }
    if (selected !== 'ky') { selected = 'en'; }
    // Public addresses are /, /contact and /privacy, with /ky/ in front for Kyrgyz.
    if (['', 'contact', 'privacy'].indexOf(route) !== -1) {
        var path = (selected === 'ky' ? '/ky/' : '/') + route;
        if (address.pathname !== path) {
            address.searchParams.delete('lang');
            window.location.replace(path + address.search + address.hash);
            return;
        }
    }
    // Hand the route's language to the initializer; language.js removes the parameter again.
    address.searchParams.set('lang', selected);
    window.history.replaceState(window.history.state, '', address.pathname + address.search + address.hash);
})();
