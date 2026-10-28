(function () {
    'use strict';
    var query = window.matchMedia('(prefers-reduced-motion: reduce)');
    var listeners = [];
    var preferences = window.linekgPreferences = {
        reducedMotion: query.matches,
        subscribe: function (listener) { listeners.push(listener); }
    };
    function updateMotion() {
        preferences.reducedMotion = query.matches;
        listeners.forEach(function (listener) { listener(preferences.reducedMotion); });
        if (window.AOS) { window.AOS.refreshHard(); }
    }
    if (query.addEventListener) { query.addEventListener('change', updateMotion); }
    else { query.addListener(updateMotion); }
    Promise.resolve(window.linekgLanguageReady).then(function () {
        if (window.AOS) {
            window.AOS.init({ once: true, disable: function () { return preferences.reducedMotion; } });
        }
    });
})();
