(function () {
    'use strict';
    var root = document.documentElement;
    var language = new URLSearchParams(window.location.search).get('lang');
    if (language !== 'en' && language !== 'ky') {
        try { language = window.localStorage.getItem('linekg.language'); } catch (error) { /* Optional storage. */ }
    }
    if (language !== 'en' && language !== 'ky') { language = 'en'; }
    root.dataset.requestedLanguage = language;
    if (language === 'ky' && root.dataset.renderedLanguage !== language) {
        root.dataset.languagePending = 'true';
        window.linekgLanguageFallbackTimer = window.setTimeout(function () {
            delete root.dataset.languagePending;
        }, 6000);
    }
})();
