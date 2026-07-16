import React, { useEffect, useMemo, useState } from 'react';
import './HomePage.css';

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1';

const MARKET_NAV_LINKS = [
  { label: 'Real Estate', category: 'real_estate' },
  { label: 'Cars', category: 'car' },
  { label: 'Watches', category: 'watch' },
  { label: 'Yachts', category: 'yacht' },
  { label: 'Jets', category: 'jet' },
  { label: 'Motorcycles', search: 'motorcycles' },
  { label: 'Helicopters', search: 'helicopters' },
  { label: 'Jewelry', category: 'jewelry' },
  { label: 'Collectibles', search: 'collectibles' },
  { label: 'Rentals', category: 'rental' },
  { label: 'Journal', path: '/journal' }
];

const AGENT_NAV_LINKS = [
  { path: '/agencies', label: 'Find Agencies' },
  { path: '/dashboard', label: 'Post Listing' },
  { path: '/concierge', label: 'Concierge Desk' }
];

const CATEGORY_OPTIONS = [
  { value: '', label: 'All Categories' },
  { value: 'real_estate', label: 'Real Estate' },
  { value: 'car', label: 'Cars' },
  { value: 'hypercar', label: 'Hypercars' },
  { value: 'yacht', label: 'Yachts' },
  { value: 'jet', label: 'Jets' },
  { value: 'watch', label: 'Watches' },
  { value: 'jewelry', label: 'Jewelry' },
  { value: 'rental', label: 'Rentals' }
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

function roleLabel(value) {
  const map = {
    standard_user: 'Buyer',
    private_seller: 'Private Seller',
    business_account: 'Business Account',
    super_admin: 'Administrator'
  };
  return map[value] || String(value || '').replaceAll('_', ' ');
}

function titleCase(value) {
  return String(value || '')
    .replaceAll('_', ' ')
    .replace(/\b\w/g, (char) => char.toUpperCase());
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
    const error = new Error(data?.detail || 'Request failed');
    error.status = res.status;
    throw error;
  }
  return data;
}

export default function HomePage() {
  const [route, setRoute] = useState(parseRoute(window.location.pathname));
  const [isScrolled, setIsScrolled] = useState(false);
  const [isNavOpen, setIsNavOpen] = useState(false);
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
  const [emailVerificationId, setEmailVerificationId] = useState(null);
  const [emailVerificationCode, setEmailVerificationCode] = useState('');
  const [emailVerificationExpiresIn, setEmailVerificationExpiresIn] = useState(null);
  const [emailVerificationDevCode, setEmailVerificationDevCode] = useState('');
  const [emailVerificationEmail, setEmailVerificationEmail] = useState('');
  const [twoFactorChallengeId, setTwoFactorChallengeId] = useState(null);
  const [twoFactorCode, setTwoFactorCode] = useState('');
  const [twoFactorExpiresIn, setTwoFactorExpiresIn] = useState(null);
  const [twoFactorDevCode, setTwoFactorDevCode] = useState('');
  const [dashboardData, setDashboardData] = useState({
    me: null,
    searches: [],
    messages: [],
    alerts: [],
    savedListings: [],
    accountSummary: null,
    adminOverview: null,
    auditLogs: [],
    moderationQueue: [],
    apiKeys: [],
    ingestionJobs: [],
    taxonomyTerms: [],
    fraudSignals: []
  });
  const [dashboardError, setDashboardError] = useState('');
  const [accountRefreshKey, setAccountRefreshKey] = useState(0);
  const [accountActionStatus, setAccountActionStatus] = useState('');
  const [newSavedSearchName, setNewSavedSearchName] = useState('');

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
    media_url: '',
    details_json: ''
  });
  const [listingCreateStatus, setListingCreateStatus] = useState('');
  const [integrationStatus, setIntegrationStatus] = useState('');
  const [apiKeyName, setApiKeyName] = useState('CRM feed key');
  const [apiKeySecret, setApiKeySecret] = useState('');
  const [ingestionSourceType, setIngestionSourceType] = useState('json');
  const [ingestionContent, setIngestionContent] = useState('');
  const [taxonomyType, setTaxonomyType] = useState('brand');
  const [taxonomyName, setTaxonomyName] = useState('');

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
    if (!token || (route.page !== 'dashboard' && route.page !== 'account')) {
      return;
    }
    let cancelled = false;
    async function loadDashboard() {
      try {
        const me = await callApi(`${API_BASE}/users/me`, {}, token);
        const [accountSummary, savedListings, searches, messages, alerts] = await Promise.all([
          callApi(`${API_BASE}/users/me/account-summary`, {}, token),
          callApi(`${API_BASE}/users/me/saved-listings`, {}, token),
          callApi(`${API_BASE}/users/me/saved-searches`, {}, token),
          callApi(`${API_BASE}/users/me/messages`, {}, token),
          callApi(`${API_BASE}/users/me/alerts`, {}, token)
        ]);
        let adminOverview = null;
        let auditLogs = [];
        let moderationQueue = [];
        let apiKeys = [];
        let ingestionJobs = [];
        let taxonomyTerms = [];
        let fraudSignals = [];
        if (['business_account', 'super_admin'].includes(me.role)) {
          [apiKeys, ingestionJobs] = await Promise.all([
            callApi(`${API_BASE}/api-keys`, {}, token).catch(() => []),
            callApi(`${API_BASE}/ingestion/jobs`, {}, token).catch(() => [])
          ]);
        }
        if (me.role === 'super_admin') {
          [adminOverview, auditLogs, moderationQueue, taxonomyTerms, fraudSignals] = await Promise.all([
            callApi(`${API_BASE}/admin/overview`, {}, token),
            callApi(`${API_BASE}/admin/audit-logs?limit=12`, {}, token),
            callApi(`${API_BASE}/admin/moderation-queue`, {}, token),
            callApi(`${API_BASE}/admin/taxonomy?include_inactive=true`, {}, token).catch(() => []),
            callApi(`${API_BASE}/admin/fraud/signals`, {}, token).catch(() => [])
          ]);
        }
        if (cancelled) return;
        setDashboardData({
          me,
          searches: accountSummary?.saved_searches || searches,
          messages: accountSummary?.inquiries || messages,
          alerts: accountSummary?.alerts || alerts,
          savedListings: accountSummary?.saved_listings || savedListings,
          accountSummary,
          adminOverview,
          auditLogs,
          moderationQueue,
          apiKeys,
          ingestionJobs,
          taxonomyTerms,
          fraudSignals
        });
        setDashboardError('');
      } catch (err) {
        if (cancelled) return;
        if (err?.status === 401) {
          localStorage.removeItem('luxline_token');
          setToken('');
          setDashboardData({
            me: null,
            searches: [],
            messages: [],
            alerts: [],
            savedListings: [],
            accountSummary: null,
            adminOverview: null,
            auditLogs: [],
            moderationQueue: [],
            apiKeys: [],
            ingestionJobs: [],
            taxonomyTerms: [],
            fraudSignals: []
          });
          setDashboardError('Session expired. Please sign in again.');
          return;
        }
        setDashboardError(err?.message || 'Unable to load dashboard right now.');
      }
    }
    loadDashboard();
    return () => {
      cancelled = true;
    };
  }, [route.page, token, accountRefreshKey]);

  function navigate(path) {
    setIsNavOpen(false);
    if (window.location.pathname === path) return;
    window.history.pushState({}, '', path);
    setRoute(parseRoute(path));
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }

  function onNavClick(event, path) {
    if (path === '/admin') return;
    event.preventDefault();
    navigate(path);
  }

  function onMarketNavClick(event, link) {
    event.preventDefault();
    setIsNavOpen(false);
    if (link.path) {
      navigate(link.path);
      return;
    }
    setCategory(link.category || '');
    setSearch(link.search || '');
    navigate('/listings');
  }

  function submitAiAsk(event) {
    event.preventDefault();
    const q = aiQuery.trim();
    if (!q) return;
    setSearch(q);
    setIsNavOpen(false);
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
      const cOk = !category || row.category === category || (category === 'car' && row.category === 'hypercar');
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
        const registerData = await callApi(`${API_BASE}/auth/register`, {
          method: 'POST',
          body: JSON.stringify(authForm)
        });
        setEmailVerificationId(registerData.email_verification_id || null);
        setEmailVerificationExpiresIn(registerData.email_otp_expires_in_seconds || null);
        setEmailVerificationDevCode(registerData.email_otp_code_dev_only || '');
        setEmailVerificationEmail(authForm.email);
        setEmailVerificationCode('');
        setAuthMessage(
          registerData.email_sent
            ? 'Verification code sent. Check your email to continue.'
            : 'Unable to send email. Use the dev code to verify.'
        );
        return;
      }

      if (twoFactorChallengeId) {
        const verifyData = await callApi(`${API_BASE}/auth/2fa/verify`, {
          method: 'POST',
          body: JSON.stringify({
            challenge_id: twoFactorChallengeId,
            code: twoFactorCode
          })
        });
        if (verifyData.access_token) {
          localStorage.setItem('luxline_token', verifyData.access_token);
          setToken(verifyData.access_token);
          setTwoFactorChallengeId(null);
          setTwoFactorCode('');
          setTwoFactorExpiresIn(null);
          setTwoFactorDevCode('');
          setAuthMessage('Logged in successfully.');
          navigate('/dashboard');
        }
        return;
      }

      const data = await callApi(`${API_BASE}/auth/login`, {
        method: 'POST',
        body: JSON.stringify({ email: authForm.email, password: authForm.password })
      });

      if (data.requires_email_verification) {
        setEmailVerificationId(data.email_verification_id || null);
        setEmailVerificationExpiresIn(data.email_otp_expires_in_seconds || null);
        setEmailVerificationDevCode(data.email_otp_code_dev_only || '');
        setEmailVerificationEmail(authForm.email);
        setEmailVerificationCode('');
        setAuthMessage(
          data.email_sent
            ? 'Email verification required. Check your inbox for the code.'
            : 'Email verification required. Use the dev code to verify.'
        );
        return;
      }

      if (data.requires_2fa) {
        setTwoFactorChallengeId(data.challenge_id || null);
        setTwoFactorCode('');
        setTwoFactorExpiresIn(data.otp_expires_in_seconds || null);
        setTwoFactorDevCode(data.otp_code_dev_only || '');
        setAuthMessage('2FA is required. Enter the 6-digit code to continue.');
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

  async function submitEmailVerification(event) {
    event.preventDefault();
    if (!emailVerificationId) return;
    setAuthMessage('Verifying email...');
    try {
      const verifyData = await callApi(`${API_BASE}/auth/email/verify`, {
        method: 'POST',
        body: JSON.stringify({
          verification_id: emailVerificationId,
          code: emailVerificationCode
        })
      });
      if (verifyData.access_token) {
        localStorage.setItem('luxline_token', verifyData.access_token);
        setToken(verifyData.access_token);
        setEmailVerificationId(null);
        setEmailVerificationCode('');
        setEmailVerificationExpiresIn(null);
        setEmailVerificationDevCode('');
        setEmailVerificationEmail('');
        setAuthMessage('Email verified. Logged in successfully.');
        navigate('/dashboard');
      }
    } catch (err) {
      setAuthMessage(err.message);
    }
  }

  async function resendEmailVerification() {
    if (!emailVerificationEmail) return;
    setAuthMessage('Sending a new verification code...');
    try {
      const data = await callApi(`${API_BASE}/auth/email/resend`, {
        method: 'POST',
        body: JSON.stringify({ email: emailVerificationEmail })
      });
      setEmailVerificationId(data.email_verification_id || null);
      setEmailVerificationExpiresIn(data.email_otp_expires_in_seconds || null);
      setEmailVerificationDevCode(data.email_otp_code_dev_only || '');
      setAuthMessage(
        data.email_sent
          ? 'New verification code sent.'
          : 'Unable to send email. Use the dev code to verify.'
      );
    } catch (err) {
      setAuthMessage(err.message);
    }
  }

  function logout() {
    localStorage.removeItem('luxline_token');
    setToken('');
    setEmailVerificationId(null);
    setEmailVerificationCode('');
    setEmailVerificationExpiresIn(null);
    setEmailVerificationDevCode('');
    setEmailVerificationEmail('');
    setTwoFactorChallengeId(null);
    setTwoFactorCode('');
    setTwoFactorExpiresIn(null);
    setTwoFactorDevCode('');
    setDashboardData({
      me: null,
      searches: [],
      messages: [],
      alerts: [],
      savedListings: [],
      accountSummary: null,
      adminOverview: null,
      auditLogs: [],
      moderationQueue: [],
      apiKeys: [],
      ingestionJobs: [],
      taxonomyTerms: [],
      fraudSignals: []
    });
    setAccountActionStatus('');
    navigate('/');
  }

  async function saveListingForAccount(listingId) {
    if (!token) {
      navigate('/dashboard');
      return;
    }
    setAccountActionStatus('Saving listing...');
    try {
      await callApi(`${API_BASE}/users/me/saved-listings/${listingId}`, { method: 'POST' }, token);
      setAccountActionStatus('Listing saved to your account.');
      setAccountRefreshKey((value) => value + 1);
    } catch (err) {
      setAccountActionStatus(err.message);
    }
  }

  async function removeSavedListing(listingId) {
    setAccountActionStatus('Removing saved listing...');
    try {
      await callApi(`${API_BASE}/users/me/saved-listings/${listingId}`, { method: 'DELETE' }, token);
      setAccountActionStatus('Saved listing removed.');
      setAccountRefreshKey((value) => value + 1);
    } catch (err) {
      setAccountActionStatus(err.message);
    }
  }

  async function saveCurrentSearch(event) {
    event.preventDefault();
    const filters = {
      search,
      category,
      currency: selectedCurrency,
      continent,
      country,
      stateProvince
    };
    const hasFilters = Object.values(filters).some(Boolean);
    setAccountActionStatus('Saving search...');
    try {
      await callApi(`${API_BASE}/users/me/saved-searches`, {
        method: 'POST',
        body: JSON.stringify({
          name: newSavedSearchName.trim() || (hasFilters ? 'Current account search' : 'All luxury inventory'),
          filters,
          alert_enabled: true
        })
      }, token);
      setNewSavedSearchName('');
      setAccountActionStatus('Saved search created with alerts enabled.');
      setAccountRefreshKey((value) => value + 1);
    } catch (err) {
      setAccountActionStatus(err.message);
    }
  }

  async function updatePreference(field, value) {
    setAccountActionStatus('Updating preference...');
    try {
      await callApi(`${API_BASE}/users/me/preferences`, {
        method: 'PATCH',
        body: JSON.stringify({ [field]: value })
      }, token);
      setAccountActionStatus('Preference updated.');
      setAccountRefreshKey((count) => count + 1);
    } catch (err) {
      setAccountActionStatus(err.message);
    }
  }

  async function toggleAlertPreference(channel, enabled) {
    setAccountActionStatus('Updating alert preference...');
    try {
      await callApi(`${API_BASE}/users/me/alerts`, {
        method: 'PUT',
        body: JSON.stringify({ channel, enabled })
      }, token);
      setAccountActionStatus('Alert preference updated.');
      setAccountRefreshKey((count) => count + 1);
    } catch (err) {
      setAccountActionStatus(err.message);
    }
  }

  async function moderateListing(listingId, action) {
    const actionLabel = action === 'approve' ? 'Approving' : 'Rejecting';
    const doneLabel = action === 'approve' ? 'approved' : 'rejected';
    setAccountActionStatus(`${actionLabel} listing...`);
    try {
      await callApi(`${API_BASE}/admin/listings/${listingId}/${action}`, {
        method: 'POST'
      }, token);
      setAccountActionStatus(`Listing ${doneLabel}.`);
      setAccountRefreshKey((count) => count + 1);
    } catch (err) {
      setAccountActionStatus(err.message);
    }
  }

  async function createApiKey(event) {
    event.preventDefault();
    setIntegrationStatus('Creating API key...');
    setApiKeySecret('');
    try {
      const data = await callApi(`${API_BASE}/api-keys`, {
        method: 'POST',
        body: JSON.stringify({ name: apiKeyName || 'CRM feed key' })
      }, token);
      setApiKeySecret(data.secret_key || '');
      setIntegrationStatus('API key created. Copy the secret now; it is shown once.');
      setAccountRefreshKey((count) => count + 1);
    } catch (err) {
      setIntegrationStatus(err.message);
    }
  }

  async function queueIngestionJob(event) {
    event.preventDefault();
    setIntegrationStatus('Queueing ingestion job...');
    try {
      await callApi(`${API_BASE}/ingestion/jobs`, {
        method: 'POST',
        body: JSON.stringify({
          source_type: ingestionSourceType,
          content: ingestionContent || null
        })
      }, token);
      setIntegrationStatus('Ingestion job queued for staging.');
      setIngestionContent('');
      setAccountRefreshKey((count) => count + 1);
    } catch (err) {
      setIntegrationStatus(err.message);
    }
  }

  async function createTaxonomyTerm(event) {
    event.preventDefault();
    setIntegrationStatus('Creating taxonomy term...');
    try {
      await callApi(`${API_BASE}/admin/taxonomy`, {
        method: 'POST',
        body: JSON.stringify({
          taxonomy: taxonomyType,
          name: taxonomyName
        })
      }, token);
      setIntegrationStatus('Taxonomy term created.');
      setTaxonomyName('');
      setAccountRefreshKey((count) => count + 1);
    } catch (err) {
      setIntegrationStatus(err.message);
    }
  }

  async function createListing(event) {
    event.preventDefault();
    setListingCreateStatus('Publishing advertisement...');
    try {
      const parsedDetails = listingForm.details_json.trim() ? JSON.parse(listingForm.details_json) : {};
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
        details: parsedDetails,
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
        media_url: '',
        details_json: ''
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
    const savedListingIds = new Set((dashboardData.savedListings || []).map((item) => item.listing_id));
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
              <button
                className="btn-outline compact"
                type="button"
                onClick={(event) => {
                  event.stopPropagation();
                  saveListingForAccount(row.id);
                }}
              >
                {savedListingIds.has(row.id) ? 'Saved' : 'Save Asset'}
              </button>
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
    const isTwoFactorStep = authMode === 'login' && !!twoFactorChallengeId;
    const isEmailVerificationStep = !!emailVerificationId;

    return (
      <form className="panel form" onSubmit={isEmailVerificationStep ? submitEmailVerification : submitAuth}>
        {isEmailVerificationStep ? (
          <>
            <p className="type">Verify Email</p>
            <p className="status">
              Enter the 6-digit code sent to {emailVerificationEmail || 'your email'}.
            </p>
            <input
              type="text"
              inputMode="numeric"
              pattern="[0-9]{6}"
              minLength={6}
              maxLength={6}
              placeholder="6-digit verification code"
              value={emailVerificationCode}
              onChange={(e) => setEmailVerificationCode(e.target.value.replace(/\D/g, '').slice(0, 6))}
              required
            />
            {emailVerificationExpiresIn ? (
              <p className="status">Code expires in about {Math.floor(emailVerificationExpiresIn / 60)} minutes.</p>
            ) : null}
            {emailVerificationDevCode ? <p className="status">Dev code: {emailVerificationDevCode}</p> : null}
            <button className="btn-solid" type="submit">Verify Email</button>
            <button className="btn-outline compact" type="button" onClick={resendEmailVerification}>
              Resend Code
            </button>
            <button
              className="btn-outline compact"
              type="button"
              onClick={() => {
                setEmailVerificationId(null);
                setEmailVerificationCode('');
                setEmailVerificationExpiresIn(null);
                setEmailVerificationDevCode('');
                setEmailVerificationEmail('');
                setAuthMessage('Email verification canceled. You can login again.');
              }}
            >
              Cancel Verification
            </button>
          </>
        ) : (
          <>
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
            <input
              type="email"
              placeholder="Email"
              value={authForm.email}
              onChange={(e) => setAuthForm((prev) => ({ ...prev, email: e.target.value }))}
              required
              disabled={isTwoFactorStep}
            />
            <input
              type="password"
              placeholder="Password"
              value={authForm.password}
              onChange={(e) => setAuthForm((prev) => ({ ...prev, password: e.target.value }))}
              required
              disabled={isTwoFactorStep}
            />
            {isTwoFactorStep ? (
              <>
                <input
                  type="text"
                  inputMode="numeric"
                  pattern="[0-9]{6}"
                  minLength={6}
                  maxLength={6}
                  placeholder="6-digit verification code"
                  value={twoFactorCode}
                  onChange={(e) => setTwoFactorCode(e.target.value.replace(/\D/g, '').slice(0, 6))}
                  required
                />
                {twoFactorExpiresIn ? <p className="status">Code expires in about {Math.floor(twoFactorExpiresIn / 60)} minutes.</p> : null}
                {twoFactorDevCode ? <p className="status">Dev code: {twoFactorDevCode}</p> : null}
              </>
            ) : null}
            <button className="btn-solid" type="submit">
              {authMode === 'login' ? (isTwoFactorStep ? 'Verify 2FA' : 'Login') : 'Create Account'}
            </button>
            <button
              className="btn-outline compact"
              type="button"
              onClick={() => {
                setAuthMode(authMode === 'login' ? 'register' : 'login');
                setTwoFactorChallengeId(null);
                setTwoFactorCode('');
                setTwoFactorExpiresIn(null);
                setTwoFactorDevCode('');
                setAuthMessage('');
              }}
            >
              {authMode === 'login' ? 'Need an account?' : 'Have an account?'}
            </button>
            {isTwoFactorStep ? (
              <button
                className="btn-outline compact"
                type="button"
                onClick={() => {
                  setTwoFactorChallengeId(null);
                  setTwoFactorCode('');
                  setTwoFactorExpiresIn(null);
                  setTwoFactorDevCode('');
                  setAuthMessage('2FA verification canceled. Login again to request a new code.');
                }}
              >
                Cancel 2FA
              </button>
            ) : null}
          </>
        )}
        {authMessage ? <p className="status">{authMessage}</p> : null}
      </form>
    );
  }

  function renderSparkline(values, stroke = '#dbb674') {
    const width = 160;
    const height = 48;
    const safeValues = values.length ? values : [0, 0, 0, 0, 0];
    const max = Math.max(...safeValues, 1);
    const min = Math.min(...safeValues, 0);
    const range = max - min || 1;
    const points = safeValues
      .map((value, idx) => {
        const x = (idx / (safeValues.length - 1 || 1)) * (width - 8) + 4;
        const y = height - 6 - ((value - min) / range) * (height - 12);
        return `${x.toFixed(1)},${y.toFixed(1)}`;
      })
      .join(' ');
    return (
      <svg className="sparkline" viewBox={`0 0 ${width} ${height}`} aria-hidden="true">
        <polyline points={points} fill="none" stroke={stroke} strokeWidth="2" />
      </svg>
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

    const currentRole = dashboardData.me?.role || '';
    const canPostListings = ['private_seller', 'business_account'].includes(currentRole);
    const canUseBrokerTools = ['business_account', 'super_admin'].includes(currentRole);
    const isDashboardAdmin = currentRole === 'super_admin';
    const userListings = listings.filter((row) => row.seller_id === dashboardData.me?.id);
    const activeListings = userListings.filter((row) => row.status === 'active');
    const pendingListings = userListings.filter((row) => row.moderation_status === 'pending');
    const draftListings = userListings.filter((row) => row.status === 'draft');
    const popularityScore = Math.min(
      100,
      20 + activeListings.length * 8 + dashboardData.messages.length * 4 + dashboardData.searches.length * 2
    );
    const adProgress = userListings.length
      ? Math.min(100, Math.round((activeListings.length / userListings.length) * 100))
      : 0;
    const exposureTrend = userListings.length
      ? [18, 24, 30, 46, 52, 58, 64]
      : [10, 14, 18, 16, 22, 20, 26];
    const inquiryTrend = dashboardData.messages.length
      ? [6, 12, 18, 22, 16, 24, 28]
      : [2, 6, 4, 8, 6, 10, 12];

    return (
      <section className="section reveal">
        <div className="section-head">
          <h2>Dashboard</h2>
          <p>Performance analytics, advertisement progress, and account signals.</p>
        </div>
        <div className="dashboard-hero">
          <article className="metric-card">
            <p className="type">Portfolio</p>
            <strong>{userListings.length}</strong>
            <span>Live listings</span>
          </article>
          <article className="metric-card">
            <p className="type">Popularity</p>
            <strong>{popularityScore}%</strong>
            <span>Audience interest</span>
          </article>
          <article className="metric-card">
            <p className="type">Ad Progress</p>
            <strong>{adProgress}%</strong>
            <span>Approved &amp; active</span>
          </article>
          <article className="metric-card">
            <p className="type">Inquiries</p>
            <strong>{dashboardData.messages.length}</strong>
            <span>Last 30 days</span>
          </article>
        </div>
        <div className="dashboard-charts">
          <article className="panel chart-card">
            <div>
              <p className="type">Exposure</p>
              <h3>Listing visibility trend</h3>
              <p>Daily views across featured placements.</p>
            </div>
            {renderSparkline(exposureTrend)}
          </article>
          <article className="panel chart-card">
            <div>
              <p className="type">Lead Flow</p>
              <h3>Inquiry momentum</h3>
              <p>Outbound buyer interest for your ads.</p>
            </div>
            {renderSparkline(inquiryTrend, '#c29a52')}
          </article>
          <article className="panel chart-card">
            <div>
              <p className="type">Advertisement Progress</p>
              <h3>Status distribution</h3>
              <p>Drafts, pending review, and active inventory.</p>
            </div>
            <div className="progress-stack">
              <div>
                <div className="progress-label">
                  <span>Active</span>
                  <span>{activeListings.length}</span>
                </div>
                <div className="progress-bar">
                  <span style={{ width: `${userListings.length ? (activeListings.length / userListings.length) * 100 : 0}%` }} />
                </div>
              </div>
              <div>
                <div className="progress-label">
                  <span>Pending</span>
                  <span>{pendingListings.length}</span>
                </div>
                <div className="progress-bar">
                  <span style={{ width: `${userListings.length ? (pendingListings.length / userListings.length) * 100 : 0}%` }} />
                </div>
              </div>
              <div>
                <div className="progress-label">
                  <span>Draft</span>
                  <span>{draftListings.length}</span>
                </div>
                <div className="progress-bar">
                  <span style={{ width: `${userListings.length ? (draftListings.length / userListings.length) * 100 : 0}%` }} />
                </div>
              </div>
            </div>
          </article>
        </div>
        <div className="dashboard-grid">
          <article className="panel">
            <h3>Profile</h3>
            <p>
              {dashboardData.me
                ? `${dashboardData.me.first_name} ${dashboardData.me.last_name}`
                : dashboardError
                  ? 'Profile unavailable'
                  : 'Loading profile...'}
            </p>
            <p>{dashboardData.me?.email || ''}</p>
            <p>Role: {roleLabel(dashboardData.me?.role)}</p>
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
        {canUseBrokerTools ? (
          <div className="account-workspace-grid">
            <article className="panel account-card">
              <p className="type">Broker API</p>
              <h3>API Keys</h3>
              <form className="inline-account-form" onSubmit={createApiKey}>
                <input
                  placeholder="Key name"
                  value={apiKeyName}
                  onChange={(e) => setApiKeyName(e.target.value)}
                />
                <button className="btn-solid" type="submit">Create Key</button>
              </form>
              {apiKeySecret ? <p className="status">{apiKeySecret}</p> : null}
              <div className="account-stack">
                {(dashboardData.apiKeys || []).length ? dashboardData.apiKeys.slice(0, 4).map((item) => (
                  <div key={item.id} className="account-row">
                    <div>
                      <strong>{item.name}</strong>
                      <p>{(item.scopes || []).join(', ') || 'No scopes'}</p>
                    </div>
                    <span>{item.revoked_at ? 'Revoked' : 'Active'}</span>
                  </div>
                )) : <p>No API keys yet.</p>}
              </div>
            </article>
            <article className="panel account-card">
              <p className="type">CRM Integration</p>
              <h3>Bulk Feed Staging</h3>
              <form className="account-stack" onSubmit={queueIngestionJob}>
                <select value={ingestionSourceType} onChange={(e) => setIngestionSourceType(e.target.value)}>
                  <option value="json">JSON</option>
                  <option value="xml">XML</option>
                  <option value="csv">CSV</option>
                </select>
                <textarea
                  rows={5}
                  placeholder="Paste feed payload for staging"
                  value={ingestionContent}
                  onChange={(e) => setIngestionContent(e.target.value)}
                />
                <button className="btn-solid" type="submit">Queue Job</button>
              </form>
              <div className="account-stack">
                {(dashboardData.ingestionJobs || []).length ? dashboardData.ingestionJobs.slice(0, 4).map((job) => (
                  <div key={job.id} className="account-row">
                    <div>
                      <strong>Job #{job.id}</strong>
                      <p>{job.source_type.toUpperCase()} · {job.total_rows} staged rows</p>
                    </div>
                    <span>{job.status}</span>
                  </div>
                )) : <p>No ingestion jobs yet.</p>}
              </div>
            </article>
          </div>
        ) : null}
        {isDashboardAdmin ? (
          <div className="account-workspace-grid">
            <article className="panel account-card">
              <p className="type">Taxonomy</p>
              <h3>Brands, Models, Builders</h3>
              <form className="inline-account-form" onSubmit={createTaxonomyTerm}>
                <select value={taxonomyType} onChange={(e) => setTaxonomyType(e.target.value)}>
                  <option value="brand">Brand</option>
                  <option value="model">Model</option>
                  <option value="builder">Builder</option>
                  <option value="material">Material</option>
                  <option value="movement">Movement</option>
                </select>
                <input
                  required
                  placeholder="Term name"
                  value={taxonomyName}
                  onChange={(e) => setTaxonomyName(e.target.value)}
                />
                <button className="btn-solid" type="submit">Add</button>
              </form>
              <div className="account-stack">
                {(dashboardData.taxonomyTerms || []).length ? dashboardData.taxonomyTerms.slice(0, 5).map((term) => (
                  <div key={term.id} className="account-row">
                    <div>
                      <strong>{term.name}</strong>
                      <p>{term.taxonomy}</p>
                    </div>
                    <span>{term.is_active ? 'Active' : 'Inactive'}</span>
                  </div>
                )) : <p>No taxonomy terms yet.</p>}
              </div>
            </article>
            <article className="panel account-card">
              <p className="type">Fraud Review</p>
              <h3>Open Signals</h3>
              <div className="account-stack">
                {(dashboardData.fraudSignals || []).length ? dashboardData.fraudSignals.slice(0, 5).map((signal) => (
                  <div key={signal.id} className="account-row">
                    <div>
                      <strong>{signal.signal_type}</strong>
                      <p>{JSON.stringify(signal.details || {})}</p>
                    </div>
                    <span>{signal.severity}</span>
                  </div>
                )) : <p>No open fraud signals.</p>}
              </div>
            </article>
          </div>
        ) : null}
        {integrationStatus ? <p className="status">{integrationStatus}</p> : null}
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
                <option value="car">Cars</option>
                <option value="hypercar">Hypercars</option>
                <option value="yacht">Yachts</option>
                <option value="jet">Jets</option>
                <option value="watch">Watches</option>
                <option value="jewelry">Jewelry</option>
                <option value="rental">Rentals</option>
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
            <textarea
              rows={4}
              placeholder='Details JSON, e.g. {"bedrooms":4,"area_value":5200,"area_unit":"sqft"}'
              value={listingForm.details_json}
              onChange={(e) => setListingForm((prev) => ({ ...prev, details_json: e.target.value }))}
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

  function renderAccountPage() {
    if (!token) {
      return (
        <section className="section reveal">
          <div className="section-head">
            <h2>Account Access</h2>
            <p>Login or register to view your account profile.</p>
          </div>
          {renderAuthCard()}
        </section>
      );
    }

    const profile = dashboardData.me;
    const summary = dashboardData.accountSummary || {};
    const savedListings = dashboardData.savedListings || [];
    const searches = dashboardData.searches || [];
    const messages = dashboardData.messages || [];
    const alerts = dashboardData.alerts || [];
    const adminOverview = dashboardData.adminOverview;
    const moderationQueue = dashboardData.moderationQueue || [];
    const isAdmin = profile?.role === 'super_admin';
    const alertEnabled = (channel) => Boolean(alerts.find((item) => item.channel === channel)?.enabled);
    const completion = summary.profile_completion ?? 0;
    const formatDate = (value) => (value ? new Date(value).toLocaleString() : '-');
    const recentActivity = [
      ...savedListings.slice(0, 2).map((item) => ({
        id: `saved-${item.id}`,
        label: 'Saved Listing',
        text: item.listing?.title || `Listing #${item.listing_id}`,
        date: item.saved_at
      })),
      ...searches.slice(0, 2).map((item) => ({
        id: `search-${item.id}`,
        label: item.alert_enabled ? 'Search Alert' : 'Saved Search',
        text: item.name,
        date: item.created_at
      })),
      ...messages.slice(0, 3).map((item) => ({
        id: `message-${item.id}`,
        label: `Inquiry ${titleCase(item.status || 'sent')}`,
        text: `Listing #${item.listing_id}`,
        date: item.replied_at || item.viewed_at || item.created_at
      }))
    ]
      .filter((item) => item.text)
      .sort((a, b) => new Date(b.date || 0) - new Date(a.date || 0))
      .slice(0, 5);

    return (
      <section className="section reveal">
        <div className="section-head">
          <h2>My Account</h2>
          <p>Profile, preferences, saved activity, alerts, and role-based controls.</p>
        </div>
        {accountActionStatus ? <p className="status">{accountActionStatus}</p> : null}
        <div className="dashboard-hero account-metrics">
          <article className="metric-card">
            <p className="type">Profile</p>
            <strong>{completion}%</strong>
            <span>Completion</span>
          </article>
          <article className="metric-card">
            <p className="type">Saved Assets</p>
            <strong>{summary.saved_listing_count ?? savedListings.length}</strong>
            <span>Watchlist</span>
          </article>
          <article className="metric-card">
            <p className="type">Searches</p>
            <strong>{summary.saved_search_count ?? searches.length}</strong>
            <span>Reusable filters</span>
          </article>
          <article className="metric-card">
            <p className="type">Inquiries</p>
            <strong>{summary.inquiry_count ?? messages.length}</strong>
            <span>Buyer and seller messages</span>
          </article>
        </div>
        <div className="account-grid">
          <article className="panel account-card">
            <p className="type">Profile</p>
            <h3>{profile ? `${profile.first_name} ${profile.last_name}` : 'Loading profile...'}</h3>
            <ul className="account-list">
              <li><span>Email</span><strong>{profile?.email || '-'}</strong></li>
              <li><span>Phone</span><strong>{profile?.phone || '-'}</strong></li>
              <li><span>Role</span><strong>{roleLabel(profile?.role)}</strong></li>
              <li><span>Status</span><strong>{profile?.is_active ? 'Active' : 'Suspended'}</strong></li>
            </ul>
          </article>
          <article className="panel account-card">
            <p className="type">Preferences</p>
            <h3>Saved Preferences</h3>
            <label>
              <span>Currency</span>
              <select value={profile?.preferred_currency || 'USD'} onChange={(e) => updatePreference('preferred_currency', e.target.value)}>
                {currencies.map((code) => <option key={code} value={code}>{code}</option>)}
              </select>
            </label>
            <label>
              <span>Language</span>
              <select value={profile?.preferred_language || 'en'} onChange={(e) => updatePreference('preferred_language', e.target.value)}>
                <option value="en">English</option>
                <option value="fr">French</option>
                <option value="es">Spanish</option>
                <option value="ar">Arabic</option>
              </select>
            </label>
            <label>
              <span>Measurement</span>
              <select value={profile?.measurement_system || 'imperial'} onChange={(e) => updatePreference('measurement_system', e.target.value)}>
                <option value="imperial">Imperial</option>
                <option value="metric">Metric</option>
              </select>
            </label>
          </article>
          <article className="panel account-card">
            <p className="type">Security</p>
            <h3>Verification</h3>
            <ul className="account-list">
              <li><span>Email verified</span><strong>{profile?.is_email_verified ? 'Yes' : 'No'}</strong></li>
              <li><span>Phone on file</span><strong>{profile?.phone ? 'Yes' : 'No'}</strong></li>
              <li><span>2FA enabled</span><strong>{profile?.is_2fa_enabled ? 'Yes' : 'No'}</strong></li>
              <li><span>Identity check</span><strong>{profile?.is_verified_business || isAdmin ? 'Verified' : 'Not submitted'}</strong></li>
            </ul>
            <button className="btn-outline compact" onClick={logout}>Logout</button>
          </article>
        </div>
        <div className="account-workspace-grid">
          <article className="panel account-card">
            <p className="type">Saved Assets</p>
            <h3>Asset Watchlist</h3>
            <div className="account-stack">
              {savedListings.length ? savedListings.slice(0, 6).map((item) => (
                <div key={item.id} className="account-row">
                  <div>
                    <strong>{item.listing?.title || `Listing #${item.listing_id}`}</strong>
                    <p>
                      {item.listing
                        ? [categoryLabel(item.listing.category), item.listing.location_city, item.listing.location_country].filter(Boolean).join(' · ')
                        : 'Listing details unavailable'}
                    </p>
                  </div>
                  <div className="account-row-actions">
                    {item.listing ? (
                      <button className="btn-outline compact" type="button" onClick={() => openListing(item.listing)}>Open</button>
                    ) : null}
                    <button className="btn-outline compact" type="button" onClick={() => removeSavedListing(item.listing_id)}>Remove</button>
                  </div>
                </div>
              )) : <p>No saved assets yet. Use Save Asset from any listing card.</p>}
            </div>
          </article>
          <article className="panel account-card">
            <p className="type">Saved Searches</p>
            <h3>Reusable Search Filters</h3>
            <form className="inline-account-form" onSubmit={saveCurrentSearch}>
              <input
                placeholder="Search name"
                value={newSavedSearchName}
                onChange={(e) => setNewSavedSearchName(e.target.value)}
              />
              <button className="btn-solid" type="submit">Save Current Search</button>
            </form>
            <div className="account-stack">
              {searches.length ? searches.slice(0, 5).map((item) => (
                <div key={item.id} className="account-row">
                  <div>
                    <strong>{item.name}</strong>
                    <p>{Object.entries(item.filters || {}).filter(([, value]) => Boolean(value)).map(([key, value]) => `${key}: ${value}`).join(' · ') || 'All inventory'}</p>
                  </div>
                  <span>{item.alert_enabled ? 'Alerts on' : 'Alerts off'}</span>
                </div>
              )) : <p>No saved searches yet.</p>}
            </div>
          </article>
          <article className="panel account-card">
            <p className="type">Alerts</p>
            <h3>Notification Channels</h3>
            <div className="alert-toggle-list">
              {['email', 'sms', 'push'].map((channel) => (
                <label key={channel} className="alert-toggle">
                  <span>{channel.toUpperCase()}</span>
                  <input
                    type="checkbox"
                    checked={alertEnabled(channel)}
                    onChange={(e) => toggleAlertPreference(channel, e.target.checked)}
                  />
                </label>
              ))}
            </div>
          </article>
          <article className="panel account-card">
            <p className="type">Inquiry History</p>
            <h3>Messages</h3>
            <div className="account-stack">
              {messages.length ? messages.slice(0, 6).map((item) => (
                <div key={item.id} className="account-row">
                  <div>
                    <strong>Listing #{item.listing_id}</strong>
                    <p>{item.message}</p>
                  </div>
                  <div className="account-row-actions">
                    <span className={`status-pill ${item.status || 'sent'}`}>{titleCase(item.status || 'sent')}</span>
                    <span>{formatDate(item.replied_at || item.viewed_at || item.created_at)}</span>
                  </div>
                </div>
              )) : <p>No inquiry history yet.</p>}
            </div>
          </article>
          <article className="panel account-card">
            <p className="type">Activity</p>
            <h3>Role-Based Activity</h3>
            <div className="account-stack">
              {recentActivity.length ? recentActivity.map((item) => (
                <div key={item.id} className="account-row">
                  <div>
                    <strong>{item.label}</strong>
                    <p>{item.text}</p>
                  </div>
                  <span>{formatDate(item.date)}</span>
                </div>
              )) : <p>No account activity yet.</p>}
            </div>
          </article>
        </div>
        {isAdmin && adminOverview ? (
          <>
            <div className="section-head account-subhead">
              <h2>Admin Workspace</h2>
              <p>Platform metrics, moderation signals, and privileged activity.</p>
            </div>
            <div className="dashboard-hero account-metrics">
              <article className="metric-card"><p className="type">Users</p><strong>{adminOverview.total_users}</strong><span>{adminOverview.active_users} active</span></article>
              <article className="metric-card"><p className="type">Listings</p><strong>{adminOverview.total_listings}</strong><span>{adminOverview.pending_listings} pending</span></article>
              <article className="metric-card"><p className="type">Inquiries</p><strong>{adminOverview.inquiry_count}</strong><span>Lead activity</span></article>
              <article className="metric-card"><p className="type">Business Review</p><strong>{adminOverview.pending_business_verifications}</strong><span>Pending checks</span></article>
            </div>
            <div className="account-workspace-grid admin-account-grid">
              <article className="panel account-card">
                <p className="type">Admin Identity</p>
                <h3>{profile ? `${profile.first_name} ${profile.last_name}` : 'Administrator'}</h3>
                <ul className="account-list">
                  <li><span>Role</span><strong>{roleLabel(profile?.role)}</strong></li>
                  <li><span>Permissions</span><strong>Users, Listings, Audit</strong></li>
                  <li><span>Account status</span><strong>{profile?.is_active ? 'Active' : 'Suspended'}</strong></li>
                  <li><span>Last login</span><strong>Current session</strong></li>
                </ul>
              </article>
              <article className="panel account-card">
                <p className="type">Moderation</p>
                <h3>Pending Review Queue</h3>
                <div className="account-stack">
                  {moderationQueue.length ? moderationQueue.slice(0, 5).map((listing) => (
                    <div key={listing.id} className="account-row">
                      <div>
                        <strong>{listing.title}</strong>
                        <p>{[categoryLabel(listing.category), listing.location_city, listing.location_country].filter(Boolean).join(' · ') || 'Pending listing'}</p>
                      </div>
                      <div className="account-row-actions">
                        <button className="btn-outline compact" type="button" onClick={() => moderateListing(listing.id, 'approve')}>Approve</button>
                        <button className="btn-outline compact" type="button" onClick={() => moderateListing(listing.id, 'reject')}>Reject</button>
                      </div>
                    </div>
                  )) : <p>No listings waiting for review.</p>}
                </div>
              </article>
              <article className="panel account-card">
                <p className="type">Audit Logs</p>
                <h3>Recent Admin Activity</h3>
                <div className="account-stack">
                  {(dashboardData.auditLogs || []).length ? dashboardData.auditLogs.map((log) => (
                    <div key={log.id} className="account-row">
                      <div>
                        <strong>{log.event_type}</strong>
                        <p>{JSON.stringify(log.details || {})}</p>
                      </div>
                      <span>{formatDate(log.created_at)}</span>
                    </div>
                  )) : <p>No audit activity yet.</p>}
                </div>
              </article>
            </div>
          </>
        ) : null}
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
      case 'account':
        return renderAccountPage();
      default:
        return renderHomePage();
    }
  }

  const authNavLinks = token
    ? [
      { path: '/dashboard', label: 'Dashboard' },
      { path: '/account', label: 'My Account' },
      { path: '/admin', label: 'Admin' }
    ]
    : [{ path: '/dashboard', label: 'Log In or Sign Up' }];

  return (
    <div className="lux-shell">
      <header className={`top-nav james-edition-nav ${isScrolled ? 'scrolled' : ''}`}>
        <div className="top-nav-main">
          <div className="nav-left">
            <button
              className={`menu-trigger ${isNavOpen ? 'active' : ''}`}
              type="button"
              aria-label="Open navigation"
              aria-expanded={isNavOpen}
              onClick={() => setIsNavOpen((value) => !value)}
            >
              <span />
              <span />
              <span />
            </button>
            <a href="/" className="brand" onClick={(e) => onNavClick(e, '/')}>Luxline</a>
          </div>

          <div className="nav-utility">
            <a href="/dashboard" onClick={(e) => onNavClick(e, '/dashboard')}>Sell With Us</a>
            <div className="agent-menu">
              <button type="button">For Agents</button>
              <div className="agent-menu-panel">
                {AGENT_NAV_LINKS.map((link) => (
                  <a key={link.path} href={link.path} onClick={(e) => onNavClick(e, link.path)}>
                    {link.label}
                  </a>
                ))}
              </div>
            </div>
            {authNavLinks.map((link) => (
              <a
                key={link.path}
                href={link.path}
                onClick={(e) => onNavClick(e, link.path)}
                className={`login-link ${route.page === link.path.slice(1) ? 'active' : ''}`}
              >
                {link.label}
              </a>
            ))}
          </div>
        </div>

        <nav className="nav-ribbon" aria-label="Marketplace categories">
          {MARKET_NAV_LINKS.map((link) => {
            const isActive = link.path
              ? route.page === link.path.slice(1)
              : route.page === 'listings' && ((link.category && category === link.category) || (link.search && search === link.search));
            return (
              <a
                key={link.label}
                href={link.path || '/listings'}
                onClick={(e) => onMarketNavClick(e, link)}
                className={isActive ? 'active' : ''}
              >
                {link.label}
              </a>
            );
          })}
        </nav>

        <div className="ai-ask-ribbon">
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

        <div className={`mobile-nav-panel ${isNavOpen ? 'open' : ''}`}>
          <nav aria-label="Mobile marketplace categories">
            {MARKET_NAV_LINKS.map((link) => (
              <a key={link.label} href={link.path || '/listings'} onClick={(e) => onMarketNavClick(e, link)}>
                {link.label}
              </a>
            ))}
          </nav>
          <div className="mobile-nav-actions">
            <a href="/dashboard" onClick={(e) => onNavClick(e, '/dashboard')}>Sell With Us</a>
            <a href="/agencies" onClick={(e) => onNavClick(e, '/agencies')}>For Agents</a>
            {authNavLinks.map((link) => (
              <a key={link.path} href={link.path} onClick={(e) => onNavClick(e, link.path)}>
                {link.label}
              </a>
            ))}
          </div>
        </div>
      </header>

      <main>{renderPage()}</main>

      <footer className="footer">
        <div>Luxline</div>
        <p>Global Luxury Marketplace · 2026 · Built for private buyers and elite agencies</p>
      </footer>
    </div>
  );
}
