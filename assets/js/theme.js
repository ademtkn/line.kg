(function($) {
    'use strict';

    if (!$ || typeof $.fn.slick !== 'function') {
        return;
    }

    var preferences = window.linekgPreferences || {
        reducedMotion: window.matchMedia('(prefers-reduced-motion: reduce)').matches
    };

    function updateDotLabels(slick) {
        if (!slick.$dots || slick.unslicked) {
            return;
        }
        // Slick's bundled ADA label uses slidesToShow as the page count even when
        // dots advance one slide at a time. Use the actual number of controls.
        var buttons = slick.$dots.find('button'),
            total = buttons.length;
        buttons.each(function(index) {
            $(this).attr('aria-label', document.documentElement.lang === 'ky' ?
                total + ' слайддын ' + (index + 1) + '-сине өтүү' :
                'Show slide ' + (index + 1) + ' of ' + total);
        });
    }

    function initializeSlider(selector, options) {
        $(selector).filter(':visible').each(function() {
            var slider = $(this),
                slideCount = slider.children(options.slide).filter(':visible').length,
                settings = $.extend(true, {}, options);
            if (!slideCount || slider.hasClass('slick-initialized')) {
                return;
            }
            settings.slidesToShow = Math.min(settings.slidesToShow, slideCount);
            settings.autoplay = false;
            settings.speed = preferences.reducedMotion ? 0 : 800;
            if (settings.responsive) {
                settings.responsive.forEach(function(breakpoint) {
                    breakpoint.settings.slidesToShow = Math.min(breakpoint.settings.slidesToShow, slideCount);
                });
            }
            slider.on('init reInit breakpoint afterChange', function(event, slick) {
                // initADA runs after init/afterChange, so update labels next frame.
                window.requestAnimationFrame(function() { updateDotLabels(slick); });
            });
            slider.slick(settings);
        });
    }

    $(function() {
        Promise.resolve(window.linekgLanguageReady).then(function() {
        initializeSlider('.categories-slider', {
            slide: '.linekg-category-item:not(.d-none):not([hidden])',
            dots: true,
            arrows: false,
            infinite: true,
            slidesToShow: document.documentElement.lang === 'ky' ? 4 : 6,
            variableWidth: false,
            slidesToScroll: 1,
            responsive: [
                { breakpoint: 1200, settings: { slidesToShow: 4 } },
                { breakpoint: 992, settings: { slidesToShow: 3 } },
                { breakpoint: 768, settings: { slidesToShow: 2 } },
                { breakpoint: 480, settings: { slidesToShow: 1 } }
            ]
        });
        initializeSlider('.testimonial-slider', {
            slide: '.linekg-testimonial-item:not(.d-none):not([hidden])',
            dots: true,
            arrows: false,
            infinite: true,
            slidesToShow: 1,
            slidesToScroll: 1
        });
        initializeSlider('.client-slider', {
            slide: '.client-item:not(.d-none):not([hidden])',
            dots: false,
            arrows: false,
            infinite: false,
            slidesToShow: 5,
            slidesToScroll: 1,
            responsive: [
                { breakpoint: 1200, settings: { slidesToShow: 4 } },
                { breakpoint: 1024, settings: { slidesToShow: 3 } },
                { breakpoint: 767, settings: { slidesToShow: 2 } },
                { breakpoint: 450, settings: { slidesToShow: 1 } }
            ]
        });

        if (typeof preferences.subscribe === 'function') {
            preferences.subscribe(function(reducedMotion) {
                $('.slick-initialized').each(function() {
                    var slick = $(this).slick('getSlick');
                    // Responsive refreshes rebuild options from originalSettings.
                    slick.originalSettings.autoplay = false;
                    slick.originalSettings.speed = reducedMotion ? 0 : 800;
                    $(this).slick('slickSetOption', {
                        autoplay: false,
                        speed: reducedMotion ? 0 : 800
                    }, false).slick('slickPause');
                });
            });
        }
        });
    });
})(window.jQuery);
