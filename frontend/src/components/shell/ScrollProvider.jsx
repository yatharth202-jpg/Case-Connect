import React, { createContext, useContext, useEffect, useState } from 'react';
import Lenis from 'lenis';

const ScrollContext = createContext({
  lenis: null,
  scrollProgress: 0,
  scrollY: 0,
});

export const useScroll = () => useContext(ScrollContext);

export const ScrollProvider = ({ children }) => {
  const [lenisInstance, setLenisInstance] = useState(null);
  const [scrollState, setScrollState] = useState({ progress: 0, y: 0 });

  useEffect(() => {
    // Respect user accessibility preference
    const prefersReduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    if (prefersReduced) {
      const handleNativeScroll = () => {
        const totalHeight = document.documentElement.scrollHeight - window.innerHeight;
        const progress = totalHeight > 0 ? window.scrollY / totalHeight : 0;
        setScrollState({ y: window.scrollY, progress });
      };
      window.addEventListener('scroll', handleNativeScroll, { passive: true });
      return () => window.removeEventListener('scroll', handleNativeScroll);
    }

    const lenis = new Lenis({
      duration: 1.2,
      easing: (t) => Math.min(1, 1.001 - Math.pow(2, -10 * t)),
      orientation: 'vertical',
      smoothWheel: true,
      touchMultiplier: 1.5,
    });

    setLenisInstance(lenis);

    let animationFrameId;
    function raf(time) {
      lenis.raf(time);
      animationFrameId = requestAnimationFrame(raf);
    }
    animationFrameId = requestAnimationFrame(raf);

    const handleLenisScroll = (e) => {
      setScrollState({
        y: e.scroll || window.scrollY,
        progress: e.progress ?? (e.scroll / (document.documentElement.scrollHeight - window.innerHeight || 1))
      });
    };

    lenis.on('scroll', handleLenisScroll);

    return () => {
      if (animationFrameId) cancelAnimationFrame(animationFrameId);
      lenis.destroy();
    };
  }, []);

  return (
    <ScrollContext.Provider value={{ lenis: lenisInstance, scrollProgress: scrollState.progress, scrollY: scrollState.y }}>
      {children}
    </ScrollContext.Provider>
  );
};

export default ScrollProvider;
