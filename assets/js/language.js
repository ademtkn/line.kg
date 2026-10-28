(function () {
    'use strict';

    var root = document.documentElement;
    var supported = ['en', 'ky'];
    var selected = root.dataset.requestedLanguage;
    var parameters = new URLSearchParams(window.location.search);
    var fallbackLanguage = supported.indexOf(root.dataset.renderedLanguage) !== -1 ? root.dataset.renderedLanguage : 'en';

    if (supported.indexOf(selected) === -1) {
        selected = parameters.get('lang');
        if (supported.indexOf(selected) === -1) {
            try { selected = window.localStorage.getItem('linekg.language'); } catch (error) { /* Storage is optional. */ }
        }
        if (supported.indexOf(selected) === -1) { selected = 'en'; }
    }

    function localizeLinks(language) {
        document.querySelectorAll('[data-localized-link]').forEach(function (link) {
            var url = new URL(link.getAttribute('href'), window.location.href);
            if (url.origin === window.location.origin) {
                url.searchParams.set('lang', language);
                link.setAttribute('href', url.pathname + url.search + url.hash);
            }
        });

        document.querySelectorAll('[data-language]').forEach(function (link) {
            var languageUrl = new URL(window.location.href);
            languageUrl.pathname = languageUrl.pathname.replace(/^\/ky\//, '/'); if (link.dataset.language === 'ky') { languageUrl.pathname = '/ky' + languageUrl.pathname; } languageUrl.searchParams.set('lang', link.dataset.language);
            link.setAttribute('href', languageUrl.pathname + languageUrl.search + languageUrl.hash);
            if (link.dataset.language === language) {
                link.setAttribute('aria-current', 'page');
            } else {
                link.removeAttribute('aria-current');
            }
        });
    }

    function updateMetadata(language) {
        if (document.body.dataset.page === 'notfound') { return; }
        var page = { home: 'index.html', contact: 'contact.html', privacy: 'privacy.html' }[document.body.dataset.page] || 'index.html';
        var base = 'https://line.kg/' + page;
        var canonical = 'https://line.kg/' + (language === 'ky' ? 'ky/' : '') + page;
        var canonicalLink = document.querySelector('link[rel="canonical"]');
        if (!canonicalLink) {
            canonicalLink = document.createElement('link');
            canonicalLink.rel = 'canonical';
            document.head.appendChild(canonicalLink);
        }
        var ogUrl = document.querySelector('meta[property="og:url"]');
        canonicalLink.href = canonical;
        if (ogUrl) { ogUrl.content = canonical; }
        document.querySelectorAll('link[rel="alternate"][hreflang]').forEach(function (link) {
            var alternate = link.getAttribute('hreflang');
            link.href = 'https://line.kg/' + (alternate === 'ky' ? 'ky/' : '') + page;
        });
        var locale = document.querySelector('meta[property="og:locale"]');
        if (locale) { locale.content = language === 'ky' ? 'ky_KG' : 'en_US'; }
        document.querySelectorAll('meta[property="og:image"], meta[name="twitter:image"]').forEach(function (image) {
            image.content = 'https://line.kg/assets/images/social/line-education-' + language + '.png';
        });
    }

    function finalize(language) {
        root.lang = language;
        localizeLinks(language);
        updateMetadata(language);
        var address = new URL(window.location.href);
        address.searchParams.set('lang', language);
        try {
            window.history.replaceState(window.history.state, '', address.pathname + address.search + address.hash);
        } catch (error) { /* File previews can have restricted history. */ }
        try { window.localStorage.setItem('linekg.language', language); } catch (error) { /* Storage is optional. */ }
        root.dataset.language = language;
        delete root.dataset.languagePending;
        window.clearTimeout(window.linekgLanguageFallbackTimer);
        measureHeader();
        return language;
    }

    function translate(dictionary) {
        var jobs = [];
        document.querySelectorAll('[data-i18n]').forEach(function (element) {
            jobs.push({ element: element, key: element.dataset.i18n });
        });
        document.querySelectorAll('[data-i18n-attrs]').forEach(function (element) {
            var attributes = JSON.parse(element.dataset.i18nAttrs);
            Object.keys(attributes).forEach(function (attribute) {
                if (!/^(alt|title|content|aria-label|aria-valuetext|placeholder)$/.test(attribute)) { return; }
                jobs.push({ element: element, key: attributes[attribute], attribute: attribute });
            });
        });
        var missing = jobs.filter(function (job) { return typeof dictionary[job.key] !== 'string'; });
        if (missing.length) { throw new Error('Missing translations: ' + missing.map(function (job) { return job.key; }).join(', ')); }
        jobs.forEach(function (job) {
            if (job.attribute) { job.element.setAttribute(job.attribute, dictionary[job.key]); }
            else { job.element.textContent = dictionary[job.key]; }
        });
    }

    // Offsets follow the rendered header after translations, font loading and zoom.
    function measureHeader() {
        var topbar = document.querySelector('.header-top');
        var navigation = document.querySelector('.header-navigation');
        root.style.setProperty('--site-topbar-offset', topbar ? Math.ceil(topbar.getBoundingClientRect().height) + 'px' : '0px');
        if (navigation) { root.style.setProperty('--site-nav-offset', Math.ceil(navigation.getBoundingClientRect().height) + 'px'); }
    }
    if (typeof window.ResizeObserver === 'function') {
        var headerObserver = new ResizeObserver(measureHeader);
        document.querySelectorAll('.header-top, .header-navigation').forEach(function (element) { headerObserver.observe(element); });
    }
    window.addEventListener('resize', measureHeader);
    window.addEventListener('hashchange', function () {
        localizeLinks(root.dataset.language || 'en');
    });
    if (document.fonts && document.fonts.ready) { document.fonts.ready.then(measureHeader); }

    if (root.dataset.renderedLanguage === selected) {
        window.linekgLanguageReady = Promise.resolve(finalize(selected));
        return;
    }

    if (typeof window.fetch !== 'function') {
        window.linekgLanguageReady = Promise.resolve(finalize(fallbackLanguage));
        return;
    }

    var script = document.querySelector('script[src*="assets/js/language.js"]');
    var dictionaryUrl = new URL('../i18n/' + selected + '.json', script.src);
    var version = document.querySelector('meta[name="linekg-i18n-version"]');
    if (version) { dictionaryUrl.searchParams.set('v', version.content); }
    var controller = typeof window.AbortController === 'function' ? new AbortController() : null;
    var timeout;
    var load = window.fetch(dictionaryUrl.href, controller ? { signal: controller.signal } : {})
        .then(function (response) {
            if (!response.ok) { throw new Error('Translation response: ' + response.status); }
            return response.json();
        });
    var deadline = new Promise(function (resolve, reject) {
        timeout = window.setTimeout(function () {
            if (controller) { controller.abort(); }
            reject(new Error('Translation loading timed out'));
        }, 5000);
    });

    window.linekgLanguageReady = Promise.race([load, deadline])
        .then(function (dictionary) {
            translate(dictionary);
            return finalize(selected);
        })
        .catch(function (error) {
            // The complete English HTML remains usable when a translation cannot load.
            console.warn('Line Education: using the rendered page because translations could not load.', error);
            return finalize(fallbackLanguage);
        })
        .finally(function () { window.clearTimeout(timeout); });
})();
