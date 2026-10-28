import React, { useEffect, useState } from 'react';

interface AmbientBackgroundProps {
  isDark?: boolean;
}

export function AmbientBackground({ isDark = true }: AmbientBackgroundProps) {
  const [mousePos, setMousePos] = useState({ x: 0, y: 0 });
  const [reducedMotion, setReducedMotion] = useState(false);

  useEffect(() => {
    const mediaQuery = window.matchMedia('(prefers-reduced-motion: reduce)');
    setReducedMotion(mediaQuery.matches);
    const handler = (e: MediaQueryListEvent) => setReducedMotion(e.matches);
    mediaQuery.addEventListener('change', handler);
    return () => mediaQuery.removeEventListener('change', handler);
  }, []);

  useEffect(() => {
    if (reducedMotion) return;

    let frameId: number;
    const handleMouseMove = (e: MouseEvent) => {
      cancelAnimationFrame(frameId);
      frameId = requestAnimationFrame(() => {
        const normalizedX = (e.clientX / window.innerWidth - 0.5) * 2;
        const normalizedY = (e.clientY / window.innerHeight - 0.5) * 2;
        setMousePos({ x: normalizedX, y: normalizedY });
      });
    };

    window.addEventListener('mousemove', handleMouseMove, { passive: true });
    return () => {
      window.removeEventListener('mousemove', handleMouseMove);
      cancelAnimationFrame(frameId);
    };
  }, [reducedMotion]);

  // Responsive parallax offsets
  const orb1X = mousePos.x * 40;
  const orb1Y = mousePos.y * 30;
  const orb2X = mousePos.x * -50;
  const orb2Y = mousePos.y * -40;
  const orb3X = mousePos.y * 35;
  const orb3Y = mousePos.x * -35;

  return (
    <div
      aria-hidden="true"
      className="fixed inset-0 pointer-events-none -z-10 overflow-hidden transition-colors duration-500"
    >
      {/* Base Foundation */}
      <div className="absolute inset-0 bg-slate-50 dark:bg-[#070b13] transition-colors duration-500" />

      {/* Atmospheric Glowing Living Wallpaper Mesh Orbs */}
      <div
        className="absolute -top-20 -left-20 w-[620px] h-[620px] rounded-full blur-[110px] transition-transform duration-700 ease-out"
        style={{
          transform: reducedMotion ? 'none' : `translate3d(${orb1X}px, ${orb1Y}px, 0)`,
          background: isDark
            ? 'radial-gradient(circle, rgba(13, 148, 136, 0.35) 0%, rgba(15, 118, 110, 0.15) 50%, transparent 70%)'
            : 'radial-gradient(circle, rgba(20, 184, 166, 0.22) 0%, rgba(13, 148, 136, 0.08) 50%, transparent 70%)',
        }}
      />

      <div
        className="absolute top-1/4 -right-32 w-[680px] h-[680px] rounded-full blur-[130px] transition-transform duration-700 ease-out"
        style={{
          transform: reducedMotion ? 'none' : `translate3d(${orb2X}px, ${orb2Y}px, 0)`,
          background: isDark
            ? 'radial-gradient(circle, rgba(79, 70, 229, 0.25) 0%, rgba(67, 56, 202, 0.10) 50%, transparent 70%)'
            : 'radial-gradient(circle, rgba(99, 102, 241, 0.14) 0%, rgba(79, 70, 229, 0.05) 50%, transparent 70%)',
        }}
      />

      <div
        className="absolute -bottom-32 left-1/3 w-[720px] h-[720px] rounded-full blur-[140px] transition-transform duration-700 ease-out"
        style={{
          transform: reducedMotion ? 'none' : `translate3d(${orb3X}px, ${orb3Y}px, 0)`,
          background: isDark
            ? 'radial-gradient(circle, rgba(6, 182, 212, 0.22) 0%, rgba(14, 116, 144, 0.10) 50%, transparent 70%)'
            : 'radial-gradient(circle, rgba(14, 165, 233, 0.12) 0%, rgba(6, 182, 212, 0.04) 50%, transparent 70%)',
        }}
      />

      {/* Precision Audit Micro-Grid Overlay */}
      <div
        className="absolute inset-0 transition-transform duration-500 ease-out opacity-25 dark:opacity-40"
        style={{
          backgroundImage: isDark
            ? 'radial-gradient(circle at 1px 1px, rgba(148, 163, 184, 0.3) 1px, transparent 0)'
            : 'radial-gradient(circle at 1px 1px, rgba(100, 116, 139, 0.35) 1px, transparent 0)',
          backgroundSize: '32px 32px',
          transform: reducedMotion ? 'none' : `translate3d(${mousePos.x * 6}px, ${mousePos.y * 6}px, 0)`,
        }}
      />

      {/* Gentle Vignette */}
      <div className="absolute inset-0 bg-gradient-to-b from-transparent via-transparent to-slate-950/20 dark:to-black/40 pointer-events-none" />
    </div>
  );
}
