import React, { useEffect, useMemo, useState } from 'react';
import './HomePage.css';

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1';

const NAV_LINKS = [
  { path: '/', label: 'Home' },
  { path: '/listings', label: 'Listings' },
  { path: '/agencies', label: 'Agencies' },
  { path: '/journal', label: 'Journal' },
  { path: '/concierge', label: 'Concierge' },
  { path: '/dashboard', label: 'Dashboard' }
];

const CATEGORY_OPTIONS = [
  { value: '', label: 'All Categories' },
  { value: 'real_estate', label: 'Real Estate' },
  { value: 'hypercar', label: 'Hypercars' },
  { value: 'yacht', label: 'Yachts' },
  { value: 'jet', label: 'Jets' },
  { value: 'watch', label: 'Watches' }
];

const FALLBACK_IMAGE_POOL = [
  'skyline.png',
  'hypercar.png',
  'yacht.png',
  'listing-penthouse.jpg',
  'listing-hypercar.jpg',
  'listing-yacht.jpg',
  'listing-private-jet.jpg',
  'luxury-lifestyle.jpg'
];

function imageUrl(fileName) {
  return `${import.meta.env.BASE_URL}image_directory/${fileName}`;
}

function money(value, code = 'USD') {
  try {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: code,
      maximumFractionDigits: 0
    }).format(Number(value || 0));
  } catch (_err) {
    return `${code} ${Number(value || 0).toLocaleString('en-US')}`;
  }
}

function categoryLabel(value) {
  return String(value || '').replaceAll('_', ' ');
}

function normalizeText(value) {
  return String(value || '').trim().toLowerCase();
}

function pathForListing(id) {
  return `/listing/${id}`;
}

function parseRoute(pathname) {
  if (pathname.startsWith('/listing/')) {
    const id = Number(pathname.split('/')[2]);
    return { page: 'listing', id: Number.isFinite(id) ? id : null };
  }
  if (pathname === '/listings') return { page: 'listings' };
  if (pathname === '/agencies') return { page: 'agencies' };
  if (pathname === '/journal') return { page: 'journal' };
  if (pathname === '/concierge') return { page: 'concierge' };
  if (pathname === '/dashboard') return { page: 'dashboard' };
  if (pathname === '/account') return { page: 'account' };
  return { page: 'home' };
}

async function callApi(url, options = {}, token = '') {
  const headers = {
    'Content-Type': 'application/json',
    ...(options.headers || {})
  };
  if (token) headers.Authorization = `Bearer ${token}`;
  const res = await fetch(url, { ...options, headers });
  const text = await res.text();
  const data = text ? JSON.parse(text) : null;
  if (!res.ok) {
    throw new Error(data?.detail || 'Request failed');
  }
  return data;
}

export default function HomePage() {
  const [route, setRoute] = useState(parseRoute(window.location.pathname));
  const [isScrolled, setIsScrolled] = useState(false);
  const [heroIndex, setHeroIndex] = useState(0);
  const [token, setToken] = useState(localStorage.getItem('luxline_token') || '');
  const [listings, setListings] = useState([]);
  const [listingsLoading, setListingsLoading] = useState(true);
  const [blogPosts, setBlogPosts] = useState([]);
  const [currencies, setCurrencies] = useState(['USD']);
  const [selectedCurrency, setSelectedCurrency] = useState('USD');
  const [search, setSearch] = useState('');
  const [aiQuery, setAiQuery] = useState('');
  const [category, setCategory] = useState('');
  const [continent, setContinent] = useState('');
  const [country, setCountry] = useState('');
  const [stateProvince, setStateProvince] = useState('');
  const [geoCountries, setGeoCountries] = useState([]);
  const [countryStateMap, setCountryStateMap] = useState({});
  const [selectedListing, setSelectedListing] = useState(null);
  const [agencyLookupId, setAgencyLookupId] = useState('1');
  const [agencyProfile, setAgencyProfile] = useState(null);
  const [agencyError, setAgencyError] = useState('');
  const [authMode, setAuthMode] = useState('login');
  const [authMessage, setAuthMessage] = useState('');
  const [dashboardData, setDashboardData] = useState({ me: null, searches: [], messages: [], alerts: [] });
  const [dashboardError, setDashboardError] = useState('');

  const [listingForm, setListingForm] = useState({
    title: '',
    description: '',
    category: 'real_estate',
    status: 'draft',
    currency: 'USD',
    price: '',
    location_country: '',
    location_city: '',
    make: '',
    model: '',
    media_url: ''
  });
  const [listingCreateStatus, setListingCreateStatus] = useState('');

  const [authForm, setAuthForm] = useState({
    email: '',
    password: '',
    first_name: '',
    last_name: '',
    phone: '',
    role: 'standard_user'
  });

  const [inquiry, setInquiry] = useState({
    listing_id: '',
    name: '',
    email: '',
    phone: '',
    message: ''
  });
  const [inquiryStatus, setInquiryStatus] = useState('');

  const heroImages = useMemo(() => {
    const listingImages = listings
      .flatMap((row) => (Array.isArray(row.media_items) ? row.media_items : []))
      .map((item) => item?.url)
      .filter(Boolean);

    const fallbackImages = FALLBACK_IMAGE_POOL.map((fileName) => imageUrl(fileName));
    const imagePool = Array.from(new Set([...listingImages, ...fallbackImages]));
    const shuffled = [...imagePool].sort(() => Math.random() - 0.5);
    return shuffled.length ? shuffled : [imageUrl('skyline.png')];
  }, [listings]);

  useEffect(() => {
    const onPopState = () => setRoute(parseRoute(window.location.pathname));
    const onScroll = () => setIsScrolled(window.scrollY > 16);
    window.addEventListener('popstate', onPopState);
    window.addEventListener('scroll', onScroll);
    onScroll();
    return () => {
      window.removeEventListener('popstate', onPopState);
      window.removeEventListener('scroll', onScroll);
    };
  }, []);

  useEffect(() => {
    setHeroIndex((v) => (heroImages.length ? v % heroImages.length : 0));
  }, [heroImages.length]);

  useEffect(() => {
    const timer = window.setInterval(() => {
      setHeroIndex((v) => (v + 1) % heroImages.length);
    }, 4800);
    return () => window.clearInterval(timer);
  }, [heroImages.length]);

  useEffect(() => {
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            entry.target.classList.add('visible');
          }
        });
      },
      { threshold: 0.18 }
    );

    document.querySelectorAll('.reveal').forEach((el) => observer.observe(el));
    return () => observer.disconnect();
  }, [route.page]);

  useEffect(() => {
    async function loadCore() {
      setListingsLoading(true);
      try {
        const [searchData, blogData, currencyData] = await Promise.all([
          callApi(`${API_BASE}/search?limit=24`),
          callApi(`${API_BASE}/monetization/blog/posts`),
          callApi(`${API_BASE}/localization/currencies`)
        ]);
        setListings(searchData.results || []);
        setBlogPosts(Array.isArray(blogData) ? blogData : []);
        const codes = Object.keys(currencyData.rates || { USD: 1 });
        setCurrencies(codes.length ? codes : ['USD']);
      } catch (_err) {
        setListings([
          {
            id: 9001,
            title: 'Monaco Bay Penthouse Residence',
            category: 'real_estate',
            price: 28000000,
            currency: 'USD',
            location_city: 'Monaco',
            location_country: 'Monaco',
            make: 'Avenue One',
            model: 'Signature Floor',
            media_items: [{ url: imageUrl('listing-penthouse.jpg') }]
          },
          {
            id: 9002,
            title: 'Aurelius V12 Carbon GT',
            category: 'hypercar',
            price: 5300000,
            currency: 'USD',
            location_city: 'Dubai',
            location_country: 'UAE',
            make: 'Aurelius',
            model: 'V12 GT',
            media_items: [{ url: imageUrl('listing-hypercar.jpg') }]
          },
          {
            id: 9003,
            title: 'Bluewater 122 Signature',
            category: 'yacht',
            price: 19000000,
            currency: 'USD',
            location_city: 'Antibes',
            location_country: 'France',
            make: 'Bluewater',
            model: '122',
            media_items: [{ url: imageUrl('listing-yacht.jpg') }]
          }
        ]);
      } finally {
        setListingsLoading(false);
      }
    }
    loadCore();
  }, []);

  useEffect(() => {
    async function loadGeoCountries() {
      try {
        const res = await fetch('https://restcountries.com/v3.1/all?fields=name,region');
        const data = await res.json();
        const rows = (Array.isArray(data) ? data : [])
          .map((row) => ({
            name: row?.name?.common || '',
            continent: row?.region || ''
          }))
          .filter((row) => row.name && row.continent);
        const unique = Array.from(
          new Map(rows.map((row) => [`${normalizeText(row.name)}|${normalizeText(row.continent)}`, row])).values()
        ).sort((a, b) => a.name.localeCompare(b.name));
        setGeoCountries(unique);
      } catch (_err) {
        setGeoCountries([]);
      }
    }
    loadGeoCountries();
  }, []);

  useEffect(() => {
    if (!country) return;
    if (countryStateMap[country]) return;

    async function loadStates() {
      try {
        const res = await fetch('https://countriesnow.space/api/v0.1/countries/states', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ country })
        });
        const data = await res.json();
        const names = (data?.data?.states || [])
          .map((row) => row?.name)
          .filter(Boolean);
        setCountryStateMap((prev) => ({ ...prev, [country]: names }));
      } catch (_err) {
        setCountryStateMap((prev) => ({ ...prev, [country]: [] }));
      }
    }
    loadStates();
  }, [country, countryStateMap]);

  useEffect(() => {
    if (route.page !== 'listing' || !route.id) {
      return;
    }
    async function loadListing() {
      try {
        const row = await callApi(`${API_BASE}/listings/${route.id}`, {}, token);
        setSelectedListing(row);
      } catch (_err) {
        setSelectedListing(null);
      }
    }
    loadListing();
  }, [route.page, route.id, token]);

  useEffect(() => {
    if (route.page !== 'dashboard' || !token) {
      return;
    }
    async function loadDashboard() {
      try {
        const [me, searches, messages, alerts] = await Promise.all([
          callApi(`${API_BASE}/users/me`, {}, token),
          callApi(`${API_BASE}/users/me/saved-searches`, {}, token),
          callApi(`${API_BASE}/users/me/messages`, {}, token),
          callApi(`${API_BASE}/users/me/alerts`, {}, token)
        ]);
        setDashboardData({ me, searches, messages, alerts });
        setDashboardError('');
      } catch (err) {
        setDashboardError(err.message);
      }
    }
    loadDashboard();
  }, [route.page, token]);

  function navigate(path) {
    if (window.location.pathname === path) return;
    window.history.pushState({}, '', path);
    setRoute(parseRoute(path));
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }

  function onNavClick(event, path) {
    event.preventDefault();
    navigate(path);
  }

  function submitAiAsk(event) {
    event.preventDefault();
    const q = aiQuery.trim();
    if (!q) return;
    setSearch(q);
    navigate('/listings');
  }

  const filteredListings = useMemo(() => {
    return listings.filter((row) => {
      const text = [row.title, row.make, row.model, row.location_city, row.location_country, row.category]
        .filter(Boolean)
        .join(' ')
        .toLowerCase();
      const q = search.trim().toLowerCase();
      const qOk = !q || text.includes(q);
      const cOk = !category || row.category === category;
      const listingCountry = normalizeText(row.location_country);
      const listingState = normalizeText(row.location_state || row.location_province || row.location_region);
      const continentForListing = normalizeText(
        geoCountries.find((geo) => normalizeText(geo.name) === listingCountry)?.continent || ''
      );
      const continentOk = !continent || continentForListing === normalizeText(continent);
      const countryOk = !country || listingCountry === normalizeText(country);
      const stateOk = !stateProvince || listingState === normalizeText(stateProvince);
      return qOk && cOk && continentOk && countryOk && stateOk;
    });
  }, [listings, search, category, continent, country, stateProvince, geoCountries]);

  const continentOptions = useMemo(() => {
    return Array.from(new Set(geoCountries.map((row) => row.continent))).sort((a, b) => a.localeCompare(b));
  }, [geoCountries]);

  const countryOptions = useMemo(() => {
    if (!continent) return [];
    return geoCountries
      .filter((row) => normalizeText(row.continent) === normalizeText(continent))
      .map((row) => row.name)
      .sort((a, b) => a.localeCompare(b));
  }, [geoCountries, continent]);

  const stateOptions = useMemo(() => {
    return country ? (countryStateMap[country] || []) : [];
  }, [country, countryStateMap]);

  function onContinentChange(value) {
    setContinent(value);
    setCountry('');
    setStateProvince('');
  }

  function onCountryChange(value) {
    setCountry(value);
    setStateProvince('');
  }

  const categoryCounts = useMemo(() => {
    const counts = {};
    listings.forEach((row) => {
      const key = row.category || 'other';
      counts[key] = (counts[key] || 0) + 1;
    });
    return counts;
  }, [listings]);

  function openListing(row) {
    navigate(pathForListing(row.id));
  }

  async function submitInquiry(event) {
    event.preventDefault();
    setInquiryStatus('Sending inquiry...');
    try {
      await callApi(`${API_BASE}/leads/listings/${Number(inquiry.listing_id)}/inquire`, {
        method: 'POST',
        body: JSON.stringify({
          name: inquiry.name,
          email: inquiry.email,
          phone: inquiry.phone,
          message: inquiry.message
        })
      }, token);
      setInquiryStatus('Inquiry sent to seller.');
      setInquiry({ listing_id: '', name: '', email: '', phone: '', message: '' });
    } catch (err) {
      setInquiryStatus(err.message);
    }
  }

  async function lookupAgency(event) {
    event.preventDefault();
    setAgencyError('');
    setAgencyProfile(null);
    try {
      const data = await callApi(`${API_BASE}/agencies/${Number(agencyLookupId)}`);
      setAgencyProfile(data);
    } catch (err) {
      setAgencyError(err.message);
    }
  }

  async function submitAuth(event) {
    event.preventDefault();
    setAuthMessage('Processing...');
    try {
      if (authMode === 'register') {
        await callApi(`${API_BASE}/auth/register`, {
          method: 'POST',
          body: JSON.stringify(authForm)
        });
        setAuthMessage('Registration complete. Login now.');
        setAuthMode('login');
        return;
      }

      const data = await callApi(`${API_BASE}/auth/login`, {
        method: 'POST',
        body: JSON.stringify({ email: authForm.email, password: authForm.password })
      });

      if (data.requires_2fa) {
        setAuthMessage('2FA is required for this account. Verify with /auth/2fa/verify from your client flow.');
        return;
      }

      if (data.access_token) {
        localStorage.setItem('luxline_token', data.access_token);
        setToken(data.access_token);
        setAuthMessage('Logged in successfully.');
        navigate('/dashboard');
      }
    } catch (err) {
      setAuthMessage(err.message);
    }
  }

  function logout() {
    localStorage.removeItem('luxline_token');
    setToken('');
    setDashboardData({ me: null, searches: [], messages: [], alerts: [] });
    navigate('/');
  }

  async function createListing(event) {
    event.preventDefault();
    setListingCreateStatus('Publishing advertisement...');
    try {
      const payload = {
        title: listingForm.title,
        description: listingForm.description || null,
        category: listingForm.category,
        status: listingForm.status,
        currency: listingForm.currency || 'USD',
        price: Number(listingForm.price || 0),
        location_country: listingForm.location_country || null,
        location_city: listingForm.location_city || null,
        make: listingForm.make || null,
        model: listingForm.model || null,
        media_items: listingForm.media_url
          ? [{ media_type: 'image', url: listingForm.media_url, sort_order: 0 }]
          : []
      };

      await callApi(`${API_BASE}/listings`, {
        method: 'POST',
        body: JSON.stringify(payload)
      }, token);

      setListingCreateStatus('Advertisement created as draft and sent for moderation.');
      setListingForm({
        title: '',
        description: '',
        category: 'real_estate',
        status: 'draft',
        currency: 'USD',
        price: '',
        location_country: '',
        location_city: '',
        make: '',
        model: '',
        media_url: ''
      });
    } catch (err) {
      setListingCreateStatus(err.message);
    }
  }

  function renderHero() {
    return (
      <section className="lux-hero reveal">
        <div className="hero-media" aria-hidden="true">
          {heroImages.map((src, idx) => (
            <figure key={src} className={`hero-slide ${idx === heroIndex ? 'active' : ''}`}>
              <img src={src} alt="" />
            </figure>
          ))}
        </div>
        <div className="hero-body">
          <p className="kicker">Global Luxury Marketplace</p>
          <h1>Private Assets. Global Access. Elite Execution.</h1>
          <p>
            Discover and transact premium real estate, hypercars, yachts, private jets, and horology through one
            curated global platform.
          </p>
          <div className="hero-actions">
            <button className="btn-solid" onClick={() => navigate('/listings')}>Explore Inventory</button>
            <button className="btn-outline" onClick={() => navigate('/concierge')}>Contact Concierge</button>
          </div>
        </div>
      </section>
    );
  }

  function renderListingGrid(rows) {
    return (
      <div className="listing-grid reveal">
        {rows.map((row, idx) => (
          <article key={row.id} className={`listing-card ${idx === 0 ? 'large' : ''}`} onClick={() => openListing(row)}>
            <img src={row.media_items?.[0]?.url || imageUrl('luxury-lifestyle.jpg')} alt={row.title} loading="lazy" />
            <div className="listing-content">
              <p className="type">{categoryLabel(row.category)}</p>
              <h3>{row.title}</h3>
              <p>{[row.make, row.model, row.location_city, row.location_country].filter(Boolean).join(' · ')}</p>
              <strong>{money(row.price, selectedCurrency || row.currency)}</strong>
            </div>
          </article>
        ))}
      </div>
    );
  }

  function renderHomePage() {
    const categoryTiles = [
      { key: 'real_estate', label: 'Private Residences', image: imageUrl('listing-penthouse.jpg') },
      { key: 'hypercar', label: 'Collector Hypercars', image: imageUrl('listing-hypercar.jpg') },
      { key: 'yacht', label: 'Superyachts', image: imageUrl('listing-yacht.jpg') },
      { key: 'jet', label: 'Private Aviation', image: imageUrl('listing-private-jet.jpg') },
      { key: 'watch', label: 'Haute Horology', image: imageUrl('luxury-lifestyle.jpg') }
    ];

    const serviceCards = [
      { title: 'Cross-Border Structuring', text: 'Tax-aware acquisition pathways across multiple jurisdictions.' },
      { title: 'Private View Scheduling', text: 'Direct introductions to owners, brokers, and family offices.' },
      { title: 'Off-Market Desk', text: 'Invitation-only supply before assets reach public inventory.' },
      { title: 'Secure Transaction Layer', text: 'Verified inquiries and controlled information release to sellers.' }
    ];

    return (
      <>
        {renderHero()}
        <section className="section reveal">
          <div className="command-center">
            <div className="command-head">
              <p className="kicker">Acquisition Command Center</p>
              <h2>Search Global Inventory in Seconds</h2>
            </div>
            <div className="command-filters">
              <input
                placeholder="Search by location, make, model, or asset name"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
              />
              <select value={category} onChange={(e) => setCategory(e.target.value)}>
                {CATEGORY_OPTIONS.map((opt) => (
                  <option key={opt.value} value={opt.value}>{opt.label}</option>
                ))}
              </select>
              <select value={selectedCurrency} onChange={(e) => setSelectedCurrency(e.target.value)}>
                {currencies.map((code) => (
                  <option key={code} value={code}>{code}</option>
                ))}
              </select>
              <button className="btn-solid" onClick={() => navigate('/listings')}>Run Search</button>
            </div>
            <div className="location-filters">
              <select value={continent} onChange={(e) => onContinentChange(e.target.value)}>
                <option value="">Select Continent</option>
                {continentOptions.map((item) => (
                  <option key={item} value={item}>{item}</option>
                ))}
              </select>
              <select value={country} onChange={(e) => onCountryChange(e.target.value)} disabled={!continent}>
                <option value="">Select Country</option>
                {countryOptions.map((item) => (
                  <option key={item} value={item}>{item}</option>
                ))}
              </select>
              <select value={stateProvince} onChange={(e) => setStateProvince(e.target.value)} disabled={!country}>
                <option value="">Select State / Province</option>
                {stateOptions.map((item) => (
                  <option key={item} value={item}>{item}</option>
                ))}
              </select>
            </div>
          </div>
        </section>
        <section className="section reveal">
          <div className="stat-ribbon">
            <article><strong>{listings.length}</strong><span>Live Listings</span></article>
            <article><strong>{Object.keys(categoryCounts).length}</strong><span>Asset Verticals</span></article>
            <article><strong>190+</strong><span>Target Cities</span></article>
            <article><strong>24/7</strong><span>Concierge Availability</span></article>
          </div>
        </section>
        <section className="section reveal">
          <div className="section-head">
            <h2>Curated Category Hubs</h2>
            <p>Dedicated discovery streams per luxury vertical.</p>
          </div>
          <div className="category-hubs">
            {categoryTiles.map((tile) => (
              <article key={tile.key} className="hub-card" onClick={() => { setCategory(tile.key); navigate('/listings'); }}>
                <img src={tile.image} alt={tile.label} loading="lazy" />
                <div>
                  <p className="type">{tile.label}</p>
                  <h3>{categoryCounts[tile.key] || 0} active opportunities</h3>
                </div>
              </article>
            ))}
          </div>
        </section>
        <section className="section reveal">
          <div className="section-head">
            <h2>Signature Inventory</h2>
            <p>Verified listings built for ultra-high-net-worth buyers and advisors.</p>
          </div>
          {listingsLoading ? <p className="status">Loading inventory...</p> : renderListingGrid(filteredListings.slice(0, 6))}
        </section>
        <section className="section reveal">
          <div className="section-head">
            <h2>White-Glove Buyer Services</h2>
            <p>Everything beyond listing discovery, handled in one channel.</p>
          </div>
          <div className="service-grid">
            {serviceCards.map((card) => (
              <article key={card.title} className="panel">
                <p className="type">Luxury Service</p>
                <h3>{card.title}</h3>
                <p>{card.text}</p>
              </article>
            ))}
          </div>
        </section>
        <section className="section reveal">
          <div className="section-head">
            <h2>Editorial Intelligence</h2>
            <p>Market briefs and directional signals for strategic acquisitions.</p>
          </div>
          <div className="journal-grid">
            {(blogPosts.length ? blogPosts.slice(0, 3) : [
              { id: 1, title: 'Global Prime Real Estate Repricing', excerpt: 'Where prestige property demand is accelerating fastest.' },
              { id: 2, title: 'Collector Car Liquidity Windows', excerpt: 'How timing affects ultra-rare vehicle exits and entries.' },
              { id: 3, title: 'Yacht + Jet Pairing Strategies', excerpt: 'Operational models for seamless dual-asset ownership.' }
            ]).map((post) => (
              <article key={post.id} className="panel">
                <p className="type">Market Report</p>
                <h3>{post.title}</h3>
                <p>{post.excerpt || 'Premium editorial brief.'}</p>
              </article>
            ))}
          </div>
        </section>
      </>
    );
  }

  function renderListingsPage() {
    return (
      <section className="section reveal">
        <div className="section-head">
          <h2>All Listings</h2>
          <p>Search, filter, and inspect assets across every category.</p>
        </div>
        <div className="filters">
          <input placeholder="Search city, make, model" value={search} onChange={(e) => setSearch(e.target.value)} />
          <select value={category} onChange={(e) => setCategory(e.target.value)}>
            {CATEGORY_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>{opt.label}</option>
            ))}
          </select>
          <select value={selectedCurrency} onChange={(e) => setSelectedCurrency(e.target.value)}>
            {currencies.map((code) => (
              <option key={code} value={code}>{code}</option>
            ))}
          </select>
        </div>
        <div className="location-filters">
          <select value={continent} onChange={(e) => onContinentChange(e.target.value)}>
            <option value="">Select Continent</option>
            {continentOptions.map((item) => (
              <option key={item} value={item}>{item}</option>
            ))}
          </select>
          <select value={country} onChange={(e) => onCountryChange(e.target.value)} disabled={!continent}>
            <option value="">Select Country</option>
            {countryOptions.map((item) => (
              <option key={item} value={item}>{item}</option>
            ))}
          </select>
          <select value={stateProvince} onChange={(e) => setStateProvince(e.target.value)} disabled={!country}>
            <option value="">Select State / Province</option>
            {stateOptions.map((item) => (
              <option key={item} value={item}>{item}</option>
            ))}
          </select>
        </div>
        {renderListingGrid(filteredListings)}
      </section>
    );
  }

  function renderListingDetailPage() {
    if (!selectedListing) {
      return (
        <section className="section reveal">
          <p className="status">Listing unavailable or not approved.</p>
        </section>
      );
    }

    return (
      <section className="section reveal">
        <button className="btn-outline compact" onClick={() => navigate('/listings')}>Back to Listings</button>
        <article className="detail-card">
          <img src={selectedListing.media_items?.[0]?.url || imageUrl('luxury-lifestyle.jpg')} alt={selectedListing.title} />
          <div>
            <p className="type">{categoryLabel(selectedListing.category)}</p>
            <h2>{selectedListing.title}</h2>
            <p>{selectedListing.description || 'Private details available via concierge only.'}</p>
            <p>{[selectedListing.make, selectedListing.model, selectedListing.year].filter(Boolean).join(' · ')}</p>
            <p>{[selectedListing.location_city, selectedListing.location_country].filter(Boolean).join(', ')}</p>
            <strong>{money(selectedListing.price, selectedCurrency || selectedListing.currency)}</strong>
          </div>
        </article>
      </section>
    );
  }

  function renderAgenciesPage() {
    return (
      <section className="section reveal">
        <div className="section-head">
          <h2>Agency Profiles</h2>
          <p>Lookup verified business profiles and active teams.</p>
        </div>
        <form className="panel" onSubmit={lookupAgency}>
          <label htmlFor="agency-id">Agency ID</label>
          <input id="agency-id" value={agencyLookupId} onChange={(e) => setAgencyLookupId(e.target.value)} />
          <button className="btn-solid" type="submit">Load Profile</button>
        </form>
        {agencyError ? <p className="status error">{agencyError}</p> : null}
        {agencyProfile ? (
          <article className="panel">
            <h3>{agencyProfile.name}</h3>
            <p>{agencyProfile.bio || 'No biography provided.'}</p>
            <p>{agencyProfile.website || agencyProfile.contact_email || 'No public contact provided.'}</p>
            <p>Team members: {agencyProfile.team_members?.length || 0}</p>
          </article>
        ) : null}
      </section>
    );
  }

  function renderJournalPage() {
    return (
      <section className="section reveal">
        <div className="section-head">
          <h2>Journal</h2>
          <p>Editorial content, reports, and market signals for elite buyers.</p>
        </div>
        <div className="journal-grid">
          {(blogPosts.length ? blogPosts : [
            { id: 1, title: 'Private Capital and Marina Demand', excerpt: 'How yacht portfolios influence coastal acquisitions.' },
            { id: 2, title: 'Hypercars as Cultural Assets', excerpt: 'Where rarity intersects with long-term value.' },
            { id: 3, title: 'Jet Mobility Strategy 2026', excerpt: 'Regional trends in private aviation ownership.' }
          ]).map((post) => (
            <article key={post.id} className="panel">
              <p className="type">Editorial</p>
              <h3>{post.title}</h3>
              <p>{post.excerpt || 'Premium editorial.'}</p>
            </article>
          ))}
        </div>
      </section>
    );
  }

  function renderConciergePage() {
    return (
      <section className="section reveal">
        <div className="section-head">
          <h2>Concierge Inquiry</h2>
          <p>Route your message to the listing seller through secure lead forms.</p>
        </div>
        <form className="panel form" onSubmit={submitInquiry}>
          <input
            required
            placeholder="Listing ID"
            value={inquiry.listing_id}
            onChange={(e) => setInquiry((prev) => ({ ...prev, listing_id: e.target.value }))}
          />
          <input
            required
            placeholder="Full name"
            value={inquiry.name}
            onChange={(e) => setInquiry((prev) => ({ ...prev, name: e.target.value }))}
          />
          <input
            type="email"
            required
            placeholder="Email"
            value={inquiry.email}
            onChange={(e) => setInquiry((prev) => ({ ...prev, email: e.target.value }))}
          />
          <input
            placeholder="Phone"
            value={inquiry.phone}
            onChange={(e) => setInquiry((prev) => ({ ...prev, phone: e.target.value }))}
          />
          <textarea
            required
            rows={5}
            placeholder="Tell us your requirements"
            value={inquiry.message}
            onChange={(e) => setInquiry((prev) => ({ ...prev, message: e.target.value }))}
          />
          <button className="btn-solid" type="submit">Send Inquiry</button>
          {inquiryStatus ? <p className="status">{inquiryStatus}</p> : null}
        </form>
      </section>
    );
  }

  function renderAuthCard() {
    return (
      <form className="panel form" onSubmit={submitAuth}>
        {authMode === 'register' ? (
          <>
            <input placeholder="First name" value={authForm.first_name} onChange={(e) => setAuthForm((prev) => ({ ...prev, first_name: e.target.value }))} required />
            <input placeholder="Last name" value={authForm.last_name} onChange={(e) => setAuthForm((prev) => ({ ...prev, last_name: e.target.value }))} required />
            <input placeholder="Phone" value={authForm.phone} onChange={(e) => setAuthForm((prev) => ({ ...prev, phone: e.target.value }))} />
            <select value={authForm.role} onChange={(e) => setAuthForm((prev) => ({ ...prev, role: e.target.value }))}>
              <option value="standard_user">Buyer</option>
              <option value="private_seller">Private Seller</option>
              <option value="business_account">Business Account</option>
            </select>
          </>
        ) : null}
        <input type="email" placeholder="Email" value={authForm.email} onChange={(e) => setAuthForm((prev) => ({ ...prev, email: e.target.value }))} required />
        <input type="password" placeholder="Password" value={authForm.password} onChange={(e) => setAuthForm((prev) => ({ ...prev, password: e.target.value }))} required />
        <button className="btn-solid" type="submit">{authMode === 'login' ? 'Login' : 'Create Account'}</button>
        <button className="btn-outline compact" type="button" onClick={() => setAuthMode(authMode === 'login' ? 'register' : 'login')}>
          {authMode === 'login' ? 'Need an account?' : 'Have an account?'}
        </button>
        {authMessage ? <p className="status">{authMessage}</p> : null}
      </form>
    );
  }

  function renderDashboardPage() {
    if (!token) {
      return (
        <section className="section reveal">
          <div className="section-head">
            <h2>Account Access</h2>
            <p>Login or register to access saved searches, alerts, and messaging history.</p>
          </div>
          {renderAuthCard()}
        </section>
      );
    }

    const canPostListings = ['private_seller', 'business_account'].includes(dashboardData.me?.role || '');

    return (
      <section className="section reveal">
        <div className="section-head">
          <h2>Dashboard</h2>
          <p>Private workspace for your account and activity.</p>
        </div>
        <div className="dashboard-grid">
          <article className="panel">
            <h3>Profile</h3>
            <p>{dashboardData.me ? `${dashboardData.me.first_name} ${dashboardData.me.last_name}` : 'Loading profile...'}</p>
            <p>{dashboardData.me?.email || ''}</p>
            <p>Role: {dashboardData.me?.role || '-'}</p>
            <button className="btn-outline compact" onClick={logout}>Logout</button>
          </article>
          <article className="panel">
            <h3>Saved Searches</h3>
            <p>{dashboardData.searches.length} saved search entries</p>
          </article>
          <article className="panel">
            <h3>Message History</h3>
            <p>{dashboardData.messages.length} inquiry messages</p>
          </article>
          <article className="panel">
            <h3>Alert Preferences</h3>
            <p>{dashboardData.alerts.length} alert channels configured</p>
          </article>
        </div>
        {canPostListings ? (
          <form className="panel form post-ad-panel" onSubmit={createListing}>
            <h3>Post Advertisement</h3>
            <input
              required
              placeholder="Title"
              value={listingForm.title}
              onChange={(e) => setListingForm((prev) => ({ ...prev, title: e.target.value }))}
            />
            <textarea
              rows={4}
              placeholder="Description"
              value={listingForm.description}
              onChange={(e) => setListingForm((prev) => ({ ...prev, description: e.target.value }))}
            />
            <div className="form-row">
              <select value={listingForm.category} onChange={(e) => setListingForm((prev) => ({ ...prev, category: e.target.value }))}>
                <option value="real_estate">Real Estate</option>
                <option value="hypercar">Hypercars</option>
                <option value="yacht">Yachts</option>
                <option value="jet">Jets</option>
                <option value="watch">Watches</option>
              </select>
              <select value={listingForm.status} onChange={(e) => setListingForm((prev) => ({ ...prev, status: e.target.value }))}>
                <option value="draft">Draft</option>
                <option value="active">Active</option>
              </select>
            </div>
            <div className="form-row">
              <input
                required
                type="number"
                min="1"
                placeholder="Price"
                value={listingForm.price}
                onChange={(e) => setListingForm((prev) => ({ ...prev, price: e.target.value }))}
              />
              <input
                placeholder="Currency (USD)"
                value={listingForm.currency}
                onChange={(e) => setListingForm((prev) => ({ ...prev, currency: e.target.value.toUpperCase() }))}
              />
            </div>
            <div className="form-row">
              <input
                placeholder="Country"
                value={listingForm.location_country}
                onChange={(e) => setListingForm((prev) => ({ ...prev, location_country: e.target.value }))}
              />
              <input
                placeholder="City"
                value={listingForm.location_city}
                onChange={(e) => setListingForm((prev) => ({ ...prev, location_city: e.target.value }))}
              />
            </div>
            <div className="form-row">
              <input
                placeholder="Make"
                value={listingForm.make}
                onChange={(e) => setListingForm((prev) => ({ ...prev, make: e.target.value }))}
              />
              <input
                placeholder="Model"
                value={listingForm.model}
                onChange={(e) => setListingForm((prev) => ({ ...prev, model: e.target.value }))}
              />
            </div>
            <input
              placeholder="Primary image URL"
              value={listingForm.media_url}
              onChange={(e) => setListingForm((prev) => ({ ...prev, media_url: e.target.value }))}
            />
            <button className="btn-solid" type="submit">Post Ad</button>
            {listingCreateStatus ? <p className="status">{listingCreateStatus}</p> : null}
          </form>
        ) : (
          <article className="panel post-ad-panel">
            <h3>Post Advertisement</h3>
            <p>Buyer accounts cannot post ads. Create a separate Private Seller or Business Account to publish ads.</p>
          </article>
        )}
        {dashboardError ? <p className="status error">{dashboardError}</p> : null}
      </section>
    );
  }

  function renderPage() {
    switch (route.page) {
      case 'listings':
        return renderListingsPage();
      case 'listing':
        return renderListingDetailPage();
      case 'agencies':
        return renderAgenciesPage();
      case 'journal':
        return renderJournalPage();
      case 'concierge':
        return renderConciergePage();
      case 'dashboard':
        return renderDashboardPage();
      default:
        return renderHomePage();
    }
  }

  return (
    <div className="lux-shell">
      <header className={`top-nav ${isScrolled ? 'scrolled' : ''}`}>
        <div className="top-nav-main">
          <a href="/" className="brand" onClick={(e) => onNavClick(e, '/')}>Luxline</a>
          <form className="ai-ask-inline" onSubmit={submitAiAsk}>
            <input
              id="ai-ask-input"
              type="text"
              value={aiQuery}
              onChange={(e) => setAiQuery(e.target.value)}
              placeholder="Ask from AI..."
            />
            <button type="submit">Ask</button>
          </form>
        </div>
        <nav className="nav-ribbon">
          {NAV_LINKS.map((link) => (
            <a key={link.path} href={link.path} onClick={(e) => onNavClick(e, link.path)} className={route.page === (link.path === '/' ? 'home' : link.path.slice(1)) ? 'active' : ''}>
              {link.label}
            </a>
          ))}
          <a href="/account" onClick={(e) => onNavClick(e, '/dashboard')}>{token ? 'My Account' : 'Login'}</a>
        </nav>
      </header>

      <main>{renderPage()}</main>

      <footer className="footer">
        <div>Luxline</div>
        <p>Global Luxury Marketplace · 2026 · Built for private buyers and elite agencies</p>
      </footer>
    </div>
  );
}

