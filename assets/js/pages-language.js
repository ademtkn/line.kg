(function () {
    'use strict';
    var address = new URL(window.location.href);
    var explicit = address.searchParams.get('lang');
    var kyrgyzPath = address.pathname.indexOf('/ky/') === 0;
    var selected = explicit;
    if (selected !== 'en' && selected !== 'ky') {
        selected = kyrgyzPath ? 'ky' : null;
        if (!selected) { try { selected = localStorage.getItem('linekg.language'); } catch (e) {} }
    }
    if (selected !== 'ky') { selected = 'en'; }
    var page = address.pathname.replace(/^\/ky\//, '/').replace(/^\//, '') || 'index.html';
    if (['index.html', 'contact.html', 'privacy.html', '404.html'].indexOf(page) !== -1) {
        var path = (selected === 'ky' ? '/ky/' : '/') + page;
        if ((selected === 'ky') !== kyrgyzPath) {
            address.pathname = path;
            window.location.replace(address.pathname + address.search + address.hash);
            return;
        }
    }
    // Let the existing language initializer prioritize this route over stored preferences.
    address.searchParams.set('lang', selected);
    window.history.replaceState(window.history.state, '', address.pathname + address.search + address.hash);
})();
