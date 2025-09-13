import React, { useState, useEffect, useRef } from "react";
import "./Home.css";
import { Link } from "react-router-dom";

/**
 * Home.jsx — interactive version
 * - Rotating empathetic messages (aria-live)
 * - Breathing technique video cards (HTML5 <video>)
 * - Keeps all existing functionality (resources modal, links)
 *
 * Note: Add short mp4/webm files to public/assets/ (breathing1.mp4, breathing2.mp4, breathing3.mp4)
 */

export default function Home() {
  const [showResources, setShowResources] = useState(false);

  // --- static content: mindfulness tips + helplines (unchanged) ---
  const mindfulnessTips = [
    {
      id: "t1",
      title: "Box Breathing",
      text: "Breathe in 4s — hold 4s — breathe out 4s — hold 4s. Repeat 4 times to reset.",
    },
    {
      id: "t2",
      title: "5-4-3-2-1 Grounding",
      text: "Name 5 things you see, 4 you feel, 3 you hear, 2 you smell, 1 you taste.",
    },
    {
      id: "t3",
      title: "Two-minute Journaling",
      text: "Write 3 lines: one thing you're grateful for, one concern, one small next step.",
    },
  ];

  const helplines = [
    { id: "h-global", label: "International / US (example)", phone: "988 / 1-800-273-8255" },
    { id: "h-in", label: "India (example)", phone: "+91-8888817666" },
    { id: "h-uk", label: "UK (example)", phone: "111 / Samaritans" },
  ];

  // --- empathy banner (rotating messages) ---
  const empathyLines = [
    "You matter — your feelings are valid.",
    "I'm here with you. Take your time.",
    "It's okay to not be okay today.",
    "Small steps are still steps — you're doing enough.",
    "Your breath can anchor you; let's try a short exercise."
  ];
  const [empathyIndex, setEmpathyIndex] = useState(0);
  const empathyRef = useRef(null);

  useEffect(() => {
    const id = setInterval(() => {
      setEmpathyIndex((i) => (i + 1) % empathyLines.length);
    }, 4200); // 4.2 seconds
    return () => clearInterval(id);
  }, []);

  // --- breathing videos (put files in public/assets/) ---
  const breathingVideos = [
    { id: "b1", title: "Box Breathing — 60s", src: "/assets/breathing1.mp4", caption: "4-4-4-4 rhythm" },
    { id: "b2", title: "4-6-8 Calm Breath", src: "/assets/breathing2.mp4", caption: "Long exhale to relax" },
    { id: "b3", title: "Guided 2-min Calm", src: "/assets/breathing3.mp4", caption: "Quick guided practice" },
  ];

  // For accessibility: announce empathy line changes
  useEffect(() => {
    if (empathyRef.current) {
      empathyRef.current.textContent = empathyLines[empathyIndex];
    }
  }, [empathyIndex]);

  return (
    <div className="home-root">
      {/* Small-screen warning */}
      <div className="mobile-warning" role="note" aria-live="polite">
        Empath is best experienced on a laptop or desktop. Please use a larger screen for full UI.
      </div>

      <div className="home-container">
        <header className="home-header">
          <div className="home-brand">
            <div className="home-logo" aria-hidden>
              <svg width="36" height="36" viewBox="0 0 24 24" fill="none">
                <circle cx="12" cy="9" r="6" fill="#7C3AED" />
                <path
                  d="M12 15c-1.1 0-2-.9-2-2 0-.74.4-1.38 1-1.72V8a1 1 0 012 0v3.28c.6.34 1 0 1 1.72 0 1.1-.9 2-2 2z"
                  fill="white"
                />
              </svg>
            </div>
            <div className="home-title-wrap">
              <h1 className="home-title">Empath</h1>
              <p className="home-sub">A private, supportive AI companion</p>
            </div>
          </div>

          <nav className="home-nav">
            <a href="#features">Features</a>
            <a href="#resources" onClick={(e) => { e.preventDefault(); setShowResources(true); }}>Resources</a>
            <a href="#privacy">Privacy</a>
            <Link className="home-cta" to="/chat">Open App</Link>
          </nav>
        </header>

        <main className="home-main">
          {/* empathy banner */}
          <div className="empathy-banner" aria-live="polite" aria-atomic="true">
            <div className="empathy-line" ref={empathyRef}>{empathyLines[empathyIndex]}</div>
            <div className="empathy-actions">
              <button className="btn-ghost small" onClick={() => setEmpathyIndex((i) => (i + 1) % empathyLines.length)}>Next</button>
              <button className="btn-ghost small" onClick={() => setEmpathyIndex(0)}>Reset</button>
            </div>
          </div>

          <section className="hero">
            <div className="hero-content">
              <h2 className="hero-title">
                A calm, confidential place to share how you really feel.
              </h2>

              <p className="hero-greeting">
                Welcome — I'm glad you're here. Empath listens without judgment. You can say as
                little or as much as you like. If you'd like, try a short grounding exercise below
                or check the resources for tips and helplines.
              </p>

              <p className="hero-desc">
                Use Empath as a daily confidant to reflect on your day, track mood, and get gentle
                coping tools and resources — not clinical advice.
              </p>

              <div className="hero-actions">
                <Link className="btn-primary" to="/chat">Open Empath</Link>
                <button className="btn-ghost" onClick={() => setShowResources(true)}>Resources</button>
              </div>

              <div className="feature-blurb">
                <div className="blurb-icon" aria-hidden>
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
                    <path
                      d="M12 2v6l4 2-4 2v6"
                      stroke="#C4B5FD"
                      strokeWidth="1.6"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    />
                  </svg>
                </div>
                <div className="blurb-text">
                  <div className="blurb-title">Daily mood check</div>
                  <div className="blurb-desc">
                    Record a quick mood and get a short prompt tailored to your state.
                  </div>
                </div>
              </div>

              {/* Breathing videos preview (inline) */}
              <div className="videos-section">
                <h4>Breathing techniques — short guided videos</h4>
                <div className="video-grid">
                  {breathingVideos.map((v) => (
                    <div key={v.id} className="video-card" aria-label={v.title}>
                      <video
                        className="video-player"
                        src={v.src}
                        controls
                        preload="metadata"
                        playsInline
                        title={v.title}
                      >
                        Sorry — your browser does not support embedded videos.
                      </video>
                      <div className="video-meta">
                        <div className="video-title">{v.title}</div>
                        <div className="video-caption">{v.caption}</div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>

            <aside className="hero-panel">
              <div className="panel-top">
                <div>
                  <div className="muted">Today</div>
                  <div className="panel-title">How are you feeling?</div>
                </div>
                <div className="muted small">Private • Local</div>
              </div>

              <div className="mood-grid">
                <button className="mood-btn">😊<span>Good</span></button>
                <button className="mood-btn">🙂<span>Okay</span></button>
                <button className="mood-btn">😞<span>Low</span></button>
              </div>

              <p className="muted note">
                Entries are private by default. Enable cloud sync in Settings.
              </p>

              <div className="exercise-card">
                <div className="exercise-title">Quick calming exercise</div>
                <div className="exercise-desc">60s box breathing to ground yourself.</div>
                <div className="exercise-actions">
                  <button className="btn-primary small">Start breathing</button>
                  <button className="btn-ghost small" onClick={() => setShowResources(true)}>Tips</button>
                </div>
              </div>
            </aside>
          </section>

          <section id="features" className="features-section">
            <h3 className="section-heading">What Empath helps with</h3>
            <div className="features-grid">
              <div className="feature">
                <div className="feature-title">Open conversation</div>
                <div className="feature-desc">
                  Share freely — Empath listens and reflects without judgment.
                </div>
              </div>
              <div className="feature">
                <div className="feature-title">Mood tracking</div>
                <div className="feature-desc">
                  Log quick mood entries and view simple trends over time.
                </div>
              </div>
              <div className="feature">
                <div className="feature-title">Practical tools</div>
                <div className="feature-desc">
                  Short grounding exercises, breathing, and journaling prompts.
                </div>
              </div>
            </div>
          </section>

          <section className="resources-preview" aria-label="Helpful resources preview">
            <div className="resources-left">
              <h4>Quick mindfulness tips</h4>
              <ul className="resource-list">
                {mindfulnessTips.map((t) => (
                  <li key={t.id} className="resource-card">
                    <div className="resource-title">{t.title}</div>
                    <div className="resource-text">{t.text}</div>
                  </li>
                ))}
              </ul>
            </div>

            <div className="resources-right">
              <h4>Helplines (examples)</h4>
              <div className="helplines">
                {helplines.map((h) => (
                  <div key={h.id} className="helpline">
                    <div className="helpline-label">{h.label}</div>
                    <div className="helpline-phone">{h.phone}</div>
                  </div>
                ))}
              </div>

              <div className="resources-cta">
                <button className="btn-primary" onClick={() => setShowResources(true)}>Open resources</button>
                <Link className="btn-ghost" to="/chat">Chat now</Link>
              </div>
            </div>
          </section>
        </main>

        <footer className="home-footer">
          <div>© {new Date().getFullYear()} Empath — Private & Non-diagnostic</div>
          <div className="muted small">Terms • Privacy</div>
        </footer>
      </div>

      {/* Resources modal (unchanged functionality) */}
      {showResources && (
        <div className="resources-modal" role="dialog" aria-modal="true" aria-label="Helpful resources">
          <div className="resources-panel">
            <div className="resources-header">
              <h3>Helpful resources</h3>
              <button className="close-x" onClick={() => setShowResources(false)}>✕</button>
            </div>

            <div className="resources-body">
              <section>
                <h4>Mindfulness tips</h4>
                <ul>
                  {mindfulnessTips.map((t) => (
                    <li key={t.id}>
                      <strong>{t.title}:</strong> {t.text}
                    </li>
                  ))}
                </ul>
              </section>

              <section>
                <h4>Helplines</h4>
                <p>If you're in immediate danger, call your local emergency number. These helplines are examples — verify for your country before calling.</p>
                <ul>
                  {helplines.map((h) => (
                    <li key={h.id}>
                      <strong>{h.label}</strong>: {h.phone}
                    </li>
                  ))}
                </ul>
              </section>

              <section>
                <h4>Quick coping ideas</h4>
                <ul>
                  <li>Take a five-minute walk outside — notice 3 new things you see.</li>
                  <li>Write a short list of things you can control right now (even small items).</li>
                  <li>Try a 60-second breathing exercise (in 4 — hold 4 — out 4 — hold 4).</li>
                </ul>
              </section>
            </div>

            <div className="resources-footer">
              <button className="btn-ghost" onClick={() => setShowResources(false)}>Close</button>
              <Link className="btn-primary" to="/chat" onClick={() => setShowResources(false)}>Start Chat</Link>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
