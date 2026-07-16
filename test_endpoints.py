"""Accurate Luxline API audit with correct paths and full auth flow."""
import requests

BASE = "http://localhost:8000"
API  = f"{BASE}/api/v1"

results = []

def r(method, path, label=None, json_body=None, headers=None, params=None, expected_fail=False):
    url = f"{API}{path}"
    try:
        resp = requests.request(method, url, json=json_body, headers=headers or {}, params=params, timeout=10)
        status = resp.status_code
        # 401/403 on auth-protected routes = working correctly
        if expected_fail:
            ok = "PASS(expected auth)" if status in (401, 403) else ("PASS" if status < 400 else "FAIL")
        else:
            ok = "PASS" if status < 400 else "FAIL"
        tag = label or f"{method} {path}"
        results.append((ok, tag, status, resp.text[:200]))
    except Exception as e:
        results.append(("FAIL", label or path, "ERR", str(e)[:200]))

# ========== HEALTH ==========
r("GET", "/health", "GET /health")
r("GET", "/", "GET / (root)")

# ========== AUTH ==========
# Register (may already exist; 400 = also acceptable)
reg = requests.post(f"{API}/auth/register", json={
    "email": "audituser@luxline.dev",
    "password": "AuditPass1234!",
    "first_name": "Audit",
    "last_name": "User",
    "role": "standard_user"
})
results.append(("PASS" if reg.status_code in (200, 201, 400) else "FAIL",
                "POST /auth/register", reg.status_code, reg.text[:200]))

# Try to get the OTP code from dev response if available
otp_code = None
verification_id = None
if reg.status_code == 201:
    rj = reg.json()
    verification_id = rj.get("email_verification_id")
    otp_code = rj.get("email_otp_code_dev_only")

# Verify email if just registered
if otp_code and verification_id:
    verify_resp = requests.post(f"{API}/auth/email/verify", json={
        "verification_id": verification_id, "code": otp_code
    })
    results.append(("PASS" if verify_resp.status_code == 200 else "FAIL",
                    "POST /auth/email/verify", verify_resp.status_code, verify_resp.text[:200]))

# Login flow
login = requests.post(f"{API}/auth/login", json={
    "email": "audituser@luxline.dev", "password": "AuditPass1234!"
})
results.append(("PASS" if login.status_code == 200 else "FAIL",
                "POST /auth/login", login.status_code, login.text[:200]))

token = ""
if login.status_code == 200:
    lj = login.json()
    token = lj.get("access_token", "")
    # Handle email verification required
    if not token and lj.get("requires_email_verification"):
        vid2 = lj.get("email_verification_id")
        otp2 = lj.get("email_otp_code_dev_only")
        if otp2 and vid2:
            v2 = requests.post(f"{API}/auth/email/verify", json={"verification_id": vid2, "code": otp2})
            if v2.status_code == 200:
                token = v2.json().get("access_token", "")

auth_h = {"Authorization": f"Bearer {token}"} if token else {}

r("GET", "/auth/me", "GET /auth/me", headers=auth_h)
r("POST", "/auth/refresh", "POST /auth/refresh", headers=auth_h)
r("POST", "/auth/logout", "POST /auth/logout", headers=auth_h)

# ========== USERS ==========
r("GET", "/users/me", "GET /users/me", headers=auth_h)
r("GET", "/users/me/saved-listings", "GET /users/me/saved-listings", headers=auth_h)
r("GET", "/users/me/saved-searches", "GET /users/me/saved-searches", headers=auth_h)
r("GET", "/users/me/alerts", "GET /users/me/alerts", headers=auth_h)
r("GET", "/users/me/messages", "GET /users/me/messages", headers=auth_h)
r("GET", "/users/me/account-summary", "GET /users/me/account-summary", headers=auth_h)

# ========== LISTINGS ==========
r("GET", "/listings", "GET /listings")
r("GET", "/real-estate/listings", "GET /real-estate/listings")
r("GET", "/cars/listings", "GET /cars/listings")
r("GET", "/yachts/listings", "GET /yachts/listings")
r("GET", "/jets/listings", "GET /jets/listings")
r("GET", "/watches/listings", "GET /watches/listings")
r("GET", "/jewelry/listings", "GET /jewelry/listings")
r("GET", "/rentals/listings", "GET /rentals/listings")

# ========== SEARCH ==========
r("GET", "/search", "GET /search")
r("GET", "/search", "GET /search?q=ferrari", params={"q": "ferrari"})
r("GET", "/search/facets", "GET /search/facets")
r("GET", "/search/autocomplete", "GET /search/autocomplete?q=rolls", params={"q": "rolls"})

# ========== LOCALIZATION ==========
r("GET", "/localization/currencies", "GET /localization/currencies")
r("GET", "/localization/convert", "GET /localization/convert", params={"amount": 100, "from": "USD", "to": "EUR"})
r("GET", "/localization/languages", "GET /localization/languages")
r("GET", "/localization/measurement-systems", "GET /localization/measurement-systems")

# ========== AGENCIES ==========
r("GET", "/agencies", "GET /agencies")

# ========== LEADS ==========
r("GET", "/leads/me/inbox", "GET /leads/me/inbox", headers=auth_h)

# ========== MESSAGING ==========
r("GET", "/messages", "GET /messages", headers=auth_h)
r("GET", "/messages/threads", "GET /messages/threads", headers=auth_h)

# ========== INGESTION ==========
r("GET", "/ingestion/feeds", "GET /ingestion/feeds", headers=auth_h, expected_fail=True)
r("GET", "/ingestion/jobs", "GET /ingestion/jobs", headers=auth_h, expected_fail=True)

# ========== MONETIZATION ==========
r("GET", "/monetization/plans", "GET /monetization/plans")
r("GET", "/monetization/subscriptions/me", "GET /monetization/subscriptions/me", headers=auth_h)
r("GET", "/monetization/blog/posts", "GET /monetization/blog/posts")

# ========== JOURNAL ==========
r("GET", "/journal/posts", "GET /journal/posts")

# ========== ADMIN (expect 401/403 without admin creds) ==========
r("GET", "/admin/users", "GET /admin/users (expect 401)", headers=auth_h, expected_fail=True)
r("GET", "/admin/overview", "GET /admin/overview (expect 401)", headers=auth_h, expected_fail=True)
r("GET", "/admin/moderation/queue", "GET /admin/moderation/queue (expect 401)", headers=auth_h, expected_fail=True)

# ========== API KEYS ==========
r("GET", "/api-keys", "GET /api-keys", headers=auth_h)

# ========== PRINT REPORT ==========
print("\n=== LUXLINE API AUDIT REPORT ===")
print(f"{'Status':<28} {'Code':<6} {'Endpoint'}")
print("-" * 80)
fails = 0
passes = 0
for ok, tag, status, body in results:
    if ok.startswith("PASS"):
        passes += 1
        icon = "+"
    else:
        fails += 1
        icon = "!"
    print(f"{icon} {ok:<26} [{status}] {tag}")
    if ok == "FAIL":
        print(f"       +- {body[:120]}")

print(f"\n=== TOTAL: {passes} PASS / {fails} FAIL ===")
