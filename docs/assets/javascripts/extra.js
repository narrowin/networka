// Hook for future JS customizations; intentionally minimal to avoid bloat

// Simple background position effect (much more reliable than complex parallax)
document.addEventListener('DOMContentLoaded', function() {
    const hero = document.querySelector('.hero');

    if (hero && window.matchMedia('(prefers-reduced-motion: no-preference)').matches) {
        window.addEventListener('scroll', function() {
            const scrolled = window.pageYOffset;
            const rate = scrolled * -0.5; // Move background up slower than scroll

            // Apply simple background position transformation
            hero.style.backgroundPosition = `center ${rate}px`;
        });
    }
});
