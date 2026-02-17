import React, { useEffect, useState } from 'react';
import './HomePage.css';

export default function HomePage() {
  const imageUrl = (fileName) => `${import.meta.env.BASE_URL}images/${fileName}`;
  const [isScrolled, setIsScrolled] = useState(false);
  const [activeHeroSlide, setActiveHeroSlide] = useState(0);

  const heroSlides = [
    {
      src: imageUrl('luxury_lifestyle.jpg'),
      alt: 'Luxury lifestyle scene',
      label: 'Private Lifestyle'
    },
    {
      src: imageUrl('private_jet.jpeg'),
      alt: 'Private jet on runway',
      label: 'Aviation'
    },
    {
      src: imageUrl('cityscraper_luxury.jpg'),
      alt: 'Luxury skyline penthouse view',
      label: 'Skyline Residences'
    }
  ];

  useEffect(() => {
    const onScroll = () => setIsScrolled(window.scrollY > 24);
    onScroll();
    window.addEventListener('scroll', onScroll);
    return () => window.removeEventListener('scroll', onScroll);
  }, []);

  useEffect(() => {
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            entry.target.classList.add('visible');
            observer.unobserve(entry.target);
          }
        });
      },
      { threshold: 0.14 }
    );

    const elements = document.querySelectorAll('.reveal');
    elements.forEach((element) => observer.observe(element));
    return () => observer.disconnect();
  }, []);

  useEffect(() => {
    const timer = window.setInterval(() => {
      setActiveHeroSlide((prev) => (prev + 1) % heroSlides.length);
    }, 4200);
    return () => window.clearInterval(timer);
  }, [heroSlides.length]);

  return (
    <div className="lux-homepage">
      <header className={`lux-header ${isScrolled ? 'scrolled' : ''}`}>
        <div className="lux-logo reveal">Luxline</div>
        <nav className="lux-nav reveal" style={{ '--stagger-delay': '90ms' }}>
          <a href="#collections">Collections</a>
          <a href="#watches">Watches</a>
          <a href="#residences">Residences</a>
          <a href="#aviation">Aviation</a>
          <a href="#contact">Contact</a>
        </nav>
        <button className="lux-nav-cta reveal" style={{ '--stagger-delay': '180ms' }}>
          Inquire for Details
        </button>
      </header>

      <section className="lux-hero reveal" style={{ '--stagger-delay': '60ms' }}>
        <div className="lux-hero-background" aria-hidden="true">
          {heroSlides.map((slide, index) => (
            <figure key={slide.src} className={`lux-hero-bg-slide ${index === activeHeroSlide ? 'active' : ''}`}>
              <img src={slide.src} alt="" />
            </figure>
          ))}
        </div>
        <div className="lux-hero-content">
          <p className="lux-kicker">Curated in Private</p>
          <h1>Ultra-Luxury Assets for a Discreet Global Circle</h1>
          <p className="lux-subtitle">
            Editorial curation of rare watches, waterfront residences, and bespoke mobility.
          </p>
        </div>
      </section>

      <section id="collections" className="lux-featured reveal" style={{ '--stagger-delay': '120ms' }}>
        <div className="lux-section-head">
          <h2>Signature Collection</h2>
          <p>Private Commission available on every listing.</p>
        </div>

        <div className="lux-editorial-grid">
          <article className="lux-card lux-card-hero reveal" style={{ '--stagger-delay': '160ms' }}>
            <div className="lux-card-image-wrap">
              <img src={imageUrl('Luxury_watch.jpg')} alt="Signature watch collection" />
            </div>
            <div className="lux-card-info">
              <p className="lux-card-type">Haute Horlogerie</p>
              <h3>Royal Chronometer Atelier Series</h3>
              <p>Private Salon Viewing | Geneva</p>
              <button className="lux-primary-btn">Inquire for Details</button>
            </div>
          </article>

          <div className="lux-stack">
            <article className="lux-card reveal" style={{ '--stagger-delay': '220ms' }}>
              <div className="lux-card-image-wrap">
                <img src={imageUrl('luxury_villa.jpg')} alt="Oceanfront estate" />
              </div>
              <div className="lux-card-info">
                <p className="lux-card-type">Estate</p>
                <h3>Seaside Glass Villa</h3>
                <p>French Riviera</p>
                <button className="lux-secondary-btn">Private Commission</button>
              </div>
            </article>

            <article className="lux-card reveal" style={{ '--stagger-delay': '280ms' }}>
              <div className="lux-card-image-wrap">
                <img src={imageUrl('private_jet.jpeg')} alt="Long range private jet" />
              </div>
              <div className="lux-card-info">
                <p className="lux-card-type">Aviation</p>
                <h3>Long-Range Flagship Jet</h3>
                <p>Worldwide Delivery</p>
                <button className="lux-secondary-btn">Private Commission</button>
              </div>
            </article>
          </div>
        </div>
      </section>

      <footer id="contact" className="lux-footer reveal" style={{ '--stagger-delay': '120ms' }}>
        <div>© 2026 Luxline. All rights reserved.</div>
      </footer>
    </div>
  );
}
