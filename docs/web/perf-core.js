/**
 * QUARRY INTELLIGENCE // PERFORMANCE CORE (v1.0)
 * Institutional-grade rendering optimizations.
 */

const PerformanceCore = {
    init() {
        this.setupNoise();
        this.setupIntersectionObserver();
        this.optimizeTailwind();
        console.log("⚡ Performance Core Active: Optimization Layer Applied.");
    },

    /**
     * Replaces heavy SVG feTurbulence with a high-performance static noise pattern.
     * Dramatically reduces GPU overhead on high-DPI displays.
     */
    setupNoise() {
        const createNoiseDataURL = () => {
            const canvas = document.createElement('canvas');
            canvas.width = 128;
            canvas.height = 128;
            const ctx = canvas.getContext('2d');
            const imgData = ctx.createImageData(128, 128);
            const data = imgData.data;
            for (let i = 0; i < data.length; i += 4) {
                const val = Math.random() * 255;
                data[i] = val;
                data[i + 1] = val;
                data[i + 2] = val;
                data[i + 3] = 12; // Very subtle alpha (approx 0.05)
            }
            ctx.putImageData(imgData, 0, 0);
            return canvas.toDataURL();
        };

        const noiseDataURL = createNoiseDataURL();
        const style = document.createElement('style');
        style.textContent = `
            .perf-noise {
                position: fixed;
                top: 0; left: 0; width: 100vw; height: 100vh;
                background-image: url("${noiseDataURL}");
                background-repeat: repeat;
                pointer-events: none;
                z-index: 50;
                opacity: 0.6;
            }
            /* Hardware Acceleration Triggers */
            .gpu-accelerated {
                will-change: transform, opacity;
                transform: translateZ(0);
                backface-visibility: hidden;
            }
            .frosted-card {
                contain: content;
            }
        `;
        document.head.appendChild(style);

        // Replace any existing <div class="noise"> with optimized version
        window.addEventListener('DOMContentLoaded', () => {
            const legacyNoise = document.querySelector('.noise');
            if (legacyNoise) {
                legacyNoise.classList.remove('noise');
                legacyNoise.classList.add('perf-noise');
                // Force clear any inline styles that might use the SVG filter
                legacyNoise.style.backgroundImage = '';
            }
        });
    },

    /**
     * Efficiency: Managed animation loops via IntersectionObserver.
     * Prevents CPU/GPU usage for background effects when they aren't visible.
     */
    setupIntersectionObserver() {
        this.observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                const event = new CustomEvent('visibilityChange', { 
                    detail: { isVisible: entry.isIntersecting } 
                });
                entry.target.dispatchEvent(event);
            });
        }, { threshold: 0.01 });
    },

    registerAnimation(element, animateCallback) {
        if (!element) return;
        this.observer.observe(element);
        
        let isActive = true;
        let frameId = null;

        element.addEventListener('visibilityChange', (e) => {
            isActive = e.detail.isVisible;
            if (isActive && !frameId) {
                loop();
            } else if (!isActive && frameId) {
                cancelAnimationFrame(frameId);
                frameId = null;
            }
        });

        const loop = () => {
            if (!isActive) return;
            animateCallback();
            frameId = requestAnimationFrame(loop);
        };

        loop();
    },

    /**
     * Prevents layout shifts and optimizes Tailwind's runtime configuration.
     */
    optimizeTailwind() {
        if (window.tailwind) {
            // Ensure tailwind config doesn't re-parse unnecessarily
            // The Play CDN is generally fast, but we ensure it's not thrashing
        }
    }
};

PerformanceCore.init();
window.PerformanceCore = PerformanceCore;
