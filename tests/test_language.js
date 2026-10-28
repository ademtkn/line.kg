// Run: node --test tests/test_language.js
// Exercise production language and keyboard-control behavior without external packages.
const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const rootPath = path.resolve(__dirname, '..');
const runtime = fs.readFileSync(path.join(rootPath, 'assets/js/language.js'), 'utf8');
const bootstrap = fs.readFileSync(path.join(rootPath, 'assets/js/language-init.js'), 'utf8');
const controls = fs.readFileSync(path.join(rootPath, 'assets/js/site.js'), 'utf8');
const dictionaries = Object.fromEntries(['en', 'ky'].map(language => [language,
    JSON.parse(fs.readFileSync(path.join(rootPath, 'assets/i18n', language + '.json'), 'utf8'))
]));
const pageNames = { home: 'index.html', contact: 'contact.html', privacy: 'privacy.html', notfound: '404.html' };

function element(attributes = {}, dataset = {}, textContent = '') {
    return {
        attributes: { ...attributes }, dataset: { ...dataset }, textContent,
        getAttribute(name) { return this.attributes[name] ?? null; },
        setAttribute(name, value) { this.attributes[name] = String(value); },
        removeAttribute(name) { delete this.attributes[name]; },
        get href() { return this.attributes.href; }, set href(value) { this.attributes.href = String(value); },
        get content() { return this.attributes.content; }, set content(value) { this.attributes.content = String(value); },
        get rel() { return this.attributes.rel; }, set rel(value) { this.attributes.rel = String(value); }
    };
}

function runBootstrap({ url = 'https://line.kg/index.html?lang=ky', stored = 'en', rendered,
    unavailableStorage = false } = {}) {
    const root = { dataset: {} }, timers = [];
    if (rendered) { root.dataset.renderedLanguage = rendered; }
    const window = {
        location: new URL(url), localStorage: { getItem() {
            if (unavailableStorage) { throw Error('Storage disabled'); }
            return stored;
        } }, setTimeout(callback, delay) { timers.push({ callback, delay }); return timers.length; }
    };
    vm.runInNewContext(bootstrap, { window, document: { documentElement: root }, URLSearchParams });
    return { root, timers };
}

async function run({ url = 'https://line.kg/contact.html?lang=ky#contact', stored = 'en', requested,
    page, rendered, unavailableStorage = false, response = 'ok', noFetch = false,
    expected = 'ky', expectFetch = !noFetch && rendered !== (requested || new URL(url).searchParams.get('lang') || stored || 'en') } = {}) {
    const originalUrl = new URL(url);
    page = page || Object.entries(pageNames).find(([, name]) => originalUrl.pathname.endsWith('/' + name))?.[0] || 'home';
    const originalLanguage = rendered === 'ky' ? 'ky' : 'en';
    const timers = new Map(), warnings = [], offsets = {};
    let timerId = 0, saved, fetched, signal;
    const root = { lang: originalLanguage, dataset: { languagePending: 'true' },
        style: { setProperty(name, value) { offsets[name] = value; } } };
    if (requested) { root.dataset.requestedLanguage = requested; }
    if (rendered) { root.dataset.renderedLanguage = rendered; }
    const titleKey = page + '.page_title';
    const text = element({}, { i18n: titleKey }, dictionaries[originalLanguage][titleKey]);
    const label = element({ 'aria-label': dictionaries[originalLanguage]['common.main_navigation'] },
        { i18nAttrs: '{"aria-label":"common.main_navigation"}' });
    // Published 404 links are root-relative so nested missing paths can recover.
    const navigation = element({ href: (page === 'notfound' ? '/' : '') + 'index.html?source=contact#services' });
    const privacy = element({ href: (page === 'notfound' ? '/' : '') + 'privacy.html?source=footer#policy' });
    const external = element({ href: 'https://moraled.com/?source=line#programs' });
    const switches = ['en', 'ky'].map(language => element({}, { language }));
    const ogUrl = element(), locale = element({ content: originalLanguage === 'ky' ? 'ky_KG' : 'en_US' });
    const images = [element(), element()];
    const alternates = page === 'notfound' ? [] : ['en', 'ky', 'x-default'].map(language => element({ hreflang: language }));
    const header = { getBoundingClientRect: () => ({ height: 85.5 }) };
    const single = {
        'script[src*="assets/js/language.js"]': { src: 'https://line.kg/assets/js/language.js?v=runtime' },
        'meta[name="linekg-i18n-version"]': { content: 'dictionary-version' },
        'meta[property="og:url"]': page === 'notfound' ? null : ogUrl,
        'meta[property="og:locale"]': locale, '.header-navigation': header
    };
    const lists = {
        '[data-i18n]': [text], '[data-i18n-attrs]': [label],
        '[data-localized-link]': [navigation, privacy, external], '[data-language]': switches,
        'link[rel="alternate"][hreflang]': alternates,
        'meta[property="og:image"], meta[name="twitter:image"]': images,
        '.header-top, .header-navigation': [header]
    };
    const document = {
        documentElement: root, body: { dataset: { page } },
        head: { appendChild(node) { single['link[rel="canonical"]'] = node; } },
        createElement: () => element(), fonts: { ready: Promise.resolve() },
        querySelector: selector => single[selector] || null,
        querySelectorAll: selector => lists[selector] || []
    };
    const window = {
        location: new URL(url),
        history: { state: null, replaceState(state, title, address) {
            window.location = new URL(address, window.location);
        } },
        localStorage: {
            getItem() { if (unavailableStorage) { throw Error('Storage disabled'); } return stored; },
            setItem(key, value) { if (unavailableStorage) { throw Error('Storage disabled'); } saved = value; }
        },
        addEventListener() {}, ResizeObserver: class { observe() {} }, AbortController,
        setTimeout(callback, delay) { timers.set(++timerId, { callback, delay }); return timerId; },
        clearTimeout(id) { timers.delete(id); }
    };
    if (!noFetch) { window.fetch = (address, options = {}) => {
        fetched = new URL(address); signal = options.signal;
        if (response === 'timeout') { return new Promise(() => {}); }
        if (response === 'network') { return Promise.reject(Error('Network unavailable')); }
        const language = path.basename(fetched.pathname, '.json');
        const dictionary = { ...dictionaries[language] };
        if (response === 'missing') { delete dictionary['common.main_navigation']; }
        return Promise.resolve({ ok: response !== '404', status: 404,
            json: () => response === 'json' ? Promise.reject(SyntaxError('Invalid JSON')) : Promise.resolve(dictionary) });
    }; }
    window.linekgLanguageFallbackTimer = window.setTimeout(() => {
        delete root.dataset.languagePending;
    }, 6000);
    vm.runInNewContext(runtime, { window, document, URL, URLSearchParams, Promise,
        ResizeObserver: window.ResizeObserver, AbortController,
        console: { warn: (...message) => warnings.push(message) } });
    if (response === 'timeout' && expectFetch) {
        [...timers.values()].find(timer => timer.delay === 5000).callback();
    }
    assert.equal(await window.linekgLanguageReady, expected);
    assert.equal(root.lang, expected);
    assert.equal(root.dataset.language, expected);
    assert.equal(root.dataset.languagePending, undefined, 'Content must be revealed');
    assert.equal(text.textContent, dictionaries[expected][titleKey], 'Content language must match the document language');
    assert.equal(label.getAttribute('aria-label'), dictionaries[expected]['common.main_navigation']);
    assert.equal(navigation.getAttribute('href'), '/index.html?source=contact&lang=' + expected + '#services');
    assert.equal(privacy.getAttribute('href'), '/privacy.html?source=footer&lang=' + expected + '#policy');
    assert.equal(external.getAttribute('href'), 'https://moraled.com/?source=line#programs', 'External links must not inherit local language parameters');
    switches.forEach((link, index) => {
        const target = new URL(originalUrl); target.searchParams.set('lang', ['en', 'ky'][index]);
        assert.equal(link.getAttribute('href'), target.pathname + target.search + target.hash);
        assert.equal(link.getAttribute('aria-current'), link.dataset.language === expected ? 'page' : null);
    });
    const address = new URL(originalUrl); address.searchParams.set('lang', expected);
    assert.equal(window.location.href, address.href, 'Final address must preserve path, other query parameters and hash');
    if (page === 'notfound') {
        assert.equal(single['link[rel="canonical"]'], undefined, 'A missing URL must never become canonical index.html');
        assert.equal(ogUrl.content, undefined);
        assert.equal(alternates.length, 0);
    } else {
        const canonical = 'https://line.kg/' + pageNames[page] + '?lang=' + expected;
        assert.equal(single['link[rel="canonical"]'].href, canonical);
        assert.equal(ogUrl.content, canonical);
        assert.equal(locale.content, expected === 'ky' ? 'ky_KG' : 'en_US');
        alternates.forEach(link => assert.equal(link.href, 'https://line.kg/' + pageNames[page] + '?lang=' +
            (link.getAttribute('hreflang') === 'ky' ? 'ky' : 'en')));
        images.forEach(image => assert.equal(image.content, 'https://line.kg/assets/images/social/line-education-' + expected + '.png'));
    }
    assert.equal(offsets['--site-topbar-offset'], '0px');
    assert.equal(offsets['--site-nav-offset'], '86px');
    assert.equal(saved, unavailableStorage ? undefined : expected);
    assert.equal(timers.size, 0, 'Both network timeout and content failsafe must be cleared');
    if (expectFetch) {
        assert.ok(fetched, 'A non-rendered language needs its dictionary');
        assert.equal(fetched.searchParams.get('v'), 'dictionary-version');
        assert.equal(warnings.length, response === 'ok' ? 0 : 1);
        if (response === 'timeout') { assert.equal(signal.aborted, true); }
    } else {
        assert.equal(fetched, undefined, 'Server-rendered content must not request a redundant dictionary');
        assert.equal(warnings.length, 0);
    }
    return fetched;
}

test('Head bootstrap prioritizes explicit language and reveals matching server-rendered Kyrgyz', () => {
    const { root, timers } = runBootstrap({ rendered: 'ky', stored: 'en' });
    assert.equal(root.dataset.requestedLanguage, 'ky');
    assert.equal(root.dataset.languagePending, undefined);
    assert.equal(timers.length, 0);
});
test('Unrendered Kyrgyz bootstrap has a failsafe and storage may be disabled', () => {
    const pending = runBootstrap({ url: 'https://line.kg/index.html', stored: 'ky' });
    assert.equal(pending.root.dataset.requestedLanguage, 'ky');
    assert.equal(pending.root.dataset.languagePending, 'true');
    pending.timers[0].callback();
    assert.equal(pending.root.dataset.languagePending, undefined);
    const english = runBootstrap({ url: 'https://line.kg/privacy.html?lang=ru', unavailableStorage: true });
    assert.equal(english.root.dataset.requestedLanguage, 'en');
});
for (const [page, name] of Object.entries(pageNames)) {
    test(page + ' loads localized content with correct metadata and page-context links', () =>
        run({ page, url: 'https://line.kg/' + name + '?lang=ky&source=share#content' }));
    for (const language of ['en', 'ky']) {
        test(page + ' matching ' + language + ' server-rendered content skips dictionary fetch', () =>
            run({ page, url: 'https://line.kg/' + name + '?lang=' + language, rendered: language,
                response: 'timeout', expected: language, expectFetch: false }));
    }
}
for (const response of ['network', '404', 'missing', 'json', 'timeout']) {
    test(response + ' failure preserves complete English content without partial translation',
        () => run({ response, expected: 'en' }));
}
test('Explicit URL language overrides saved preference', async () => {
    assert.equal((await run({ url: 'https://line.kg/index.html?lang=en&source=share#services',
        stored: 'ky', expected: 'en' })).pathname, '/assets/i18n/en.json');
});
test('Saved language is used when the URL has no language', async () => {
    assert.equal((await run({ url: 'https://line.kg/privacy.html#policy', stored: 'ky' })).pathname,
        '/assets/i18n/ky.json');
});
test('Unavailable storage permits explicit Kyrgyz and defaults unspecified requests to English', async () => {
    await run({ unavailableStorage: true });
    await run({ url: 'https://line.kg/contact.html#contact', unavailableStorage: true, expected: 'en', expectFetch: true });
});
test('Language captured by the external head bootstrap remains authoritative', async () => {
    assert.equal((await run({ url: 'https://line.kg/contact.html?lang=en', requested: 'ky', stored: 'en', expectFetch: true })).pathname,
        '/assets/i18n/ky.json');
});
test('Mismatched SSR language fetches the requested language, with native URL context preserved', () =>
    run({ rendered: 'en', url: 'https://line.kg/privacy.html?lang=ky&ref=mail#policy' }));
test('A failed request on Kyrgyz SSR preserves Kyrgyz content and language declaration', () =>
    run({ rendered: 'ky', url: 'https://line.kg/privacy.html?lang=en', response: 'network', expected: 'ky' }));
test('Missing fetch support reveals existing SSR content without inventing an English translation', () =>
    run({ rendered: 'ky', url: 'https://line.kg/privacy.html?lang=en', noFetch: true, expected: 'ky' }));
test('A nested missing URL stays a noncanonical 404 after language initialization', () =>
    run({ page: 'notfound', url: 'https://line.kg/missing/folder.html?lang=ky&ref=broken#target' }));

function runControls() {
    let focused, mainFocus;
    const panels = new Map();
    const buttons = [0, 1, 2, 3].map(index => {
        const node = element({ 'aria-controls': 'panel-' + index, 'aria-expanded': index === 0 ? 'true' : 'false' });
        node.events = {};
        node.addEventListener = (type, handler) => { node.events[type] = handler; };
        node.focus = () => { focused = index; };
        const classes = new Set(index === 0 ? ['show'] : []);
        panels.set('panel-' + index, { classList: { toggle(name, add) {
            if (add) { classes.add(name); } else { classes.delete(name); }
        }, contains(name) { return classes.has(name); } } });
        return node;
    });
    const skip = { addEventListener(type, handler) { this[type] = handler; } };
    const main = { focus(options) { mainFocus = options; } };
    const document = {
        querySelectorAll(selector) { return selector === '.accordion' ? [{ querySelectorAll: () => buttons }] : [skip]; },
        getElementById(id) { return id === 'main-content' ? main : panels.get(id); }
    };
    vm.runInNewContext(controls, { document });
    return { buttons, panels, skip, focused: () => focused, mainFocus: () => mainFocus };
}
test('Native FAQ control opens only the requested panel and can close it', () => {
    const { buttons, panels } = runControls();
    buttons[1].events.click();
    buttons.forEach((button, index) => {
        assert.equal(button.getAttribute('aria-expanded'), String(index === 1));
        assert.equal(panels.get('panel-' + index).classList.contains('show'), index === 1);
    });
    buttons[1].events.click();
    buttons.forEach(button => assert.equal(button.getAttribute('aria-expanded'), 'false'));
});
test('FAQ arrows wrap focus and Home/End select first/last questions', () => {
    const { buttons, focused } = runControls();
    let prevented = 0;
    const key = (index, value) => buttons[index].events.keydown({ key: value, preventDefault() { prevented++; } });
    key(3, 'ArrowDown'); assert.equal(focused(), 0);
    key(0, 'ArrowUp'); assert.equal(focused(), 3);
    key(2, 'Home'); assert.equal(focused(), 0);
    key(1, 'End'); assert.equal(focused(), 3);
    assert.equal(prevented, 4);
});
test('Skip link moves keyboard focus to main without replacing native anchor scrolling', () => {
    const { skip, mainFocus } = runControls();
    skip.click();
    assert.equal(mainFocus().preventScroll, true);
});
