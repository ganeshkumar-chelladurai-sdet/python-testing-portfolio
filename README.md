# Python + PyTest Testing Portfolio

![Tests](https://github.com/ganeshkumar-chelladurai-sdet/python-testing-portfolio/actions/workflows/tests.yml/badge.svg)

A single, self-contained project demonstrating UI, API, and ETL/data-pipeline
testing with **Python and PyTest only** — built to close a specific gap:
Python/PyTest keeps showing up across QA/SDET job descriptions in Ireland,
separately from the Java/Selenium framework in my other repo. What started
as three simple, isolated demo targets has grown into a real, relational
system: a SQLite-backed customer database, a second related entity (credit
reports), two independent authentication layers, and a genuine UI beyond a
login form — all with 31 tests and dual CI/CD, entirely hand-typed and
personally understood, guided but never generated wholesale.

## System overview

- **`mock_target/app.py`** — a Flask app serving two things: a browser-facing
  UI (login page, gated by a real session cookie, and a dashboard listing
  live customer data) and a JSON API (`/api/customers`, `/api/customers/<id>/credit-reports`,
  `/api/credit-reports/<id>`), protected by short-lived bearer tokens issued
  through `/api/login`.
- **SQLite database** — two related tables: `customers` (with a `flagged`
  column set by the ETL pipeline) and `credit_reports` (foreign-keyed to
  `customers`). A test-only `init_db(reset=True)` call, wired into an
  `autouse` PyTest fixture, guarantees every single test in the suite starts
  from an identical, known state.
- **`mock_target/etl/pipeline.py`** — loads two overlapping CSV extracts,
  dedupes by normalized email, flags records outside a credit-score
  threshold, validates referential integrity on a separate incoming-reports
  extract, and loads everything into the same live database the API reads
  from.

## How each module maps to real experience

| Module | What it tests | Maps to |
|---|---|---|
| `tests/ui/` | Login form, session-gated dashboard, dynamic waits instead of fixed sleeps, Page Object Model | Enterprise UI automation frameworks in a commercial financial-services environment — ~30% regression coverage improvement |
| `tests/api/test_customers.py`, `test_credit_reports.py` | Full CRUD lifecycle, JSON schema validation, negative-path/error-code handling, a proven security property (PUT field whitelist) | Enterprise API/DB validation using REST Assured & Postman; SQL testing across commercial-scale projects |
| `tests/api/test_auth.py` | Missing/invalid/expired bearer tokens, a test-only endpoint gated behind an environment flag to simulate expiry safely | General production-readiness discipline — auth isn't optional on a real API |
| `tests/etl/` | Dedupe by normalized email, credit-score threshold validation with explicit boundary cases, referential-integrity validation, real database writes | Commercial ETL/data-pipeline validation (~99% data integrity) and enterprise data validation across financial-services products, done here in pandas + SQL instead of a GUI-based enterprise ETL tool |
| `Jenkinsfile` + local Jenkins | API + ETL suites run automatically on every push via Poll SCM | Enterprise CI/CD integration via Jenkins in a commercial setting — ~20% release cycle time reduction |
| `.github/workflows/tests.yml` | Full 31-test suite (UI + API + ETL) on every push, cloud-hosted | Same CI discipline, scoped to run publicly and cover everything including the browser-dependent UI suite |

## Continuous integration

Two CI pipelines, deliberately scoped differently:

- **GitHub Actions** (badge above) runs the complete suite — all 31 tests,
  including the Playwright UI tests — on a clean cloud VM on every push.
  This is the one anyone can verify by clicking the badge.
- **Jenkins**, run locally via Docker rather than publicly hosted (a public
  Jenkins instance is a real security exposure, and it isn't needed to make
  the point). Scoped to the API and ETL suites, and polls GitHub every 5
  minutes for new commits (`H/5 * * * *`) rather than relying on a webhook,
  since that would require exposing a local instance to the public internet.
  Chosen specifically because Jenkins is the CI tool actually listed on my
  resume and used at TransUnion, not just a generic choice.

  ![Jenkins pipeline passing](docs/jenkins-success.png)

Both pipelines start the Flask app with `ENABLE_TEST_ENDPOINTS=1` — the
expired-token test needs a way to simulate expiry over real HTTP, and that
flag gates a test-only route (`/api/test/expire-token`) that's genuinely
absent from the app's routing table unless explicitly enabled, never live in
a normal run.

## Structure

mock_target/
  app.py                     # Flask app: session-gated UI, token-gated API, SQLite-backed
  templates/
    login.html
    dashboard.html
  etl/pipeline.py             # load -> merge -> dedupe -> threshold/referential validate -> load into DB
  data/                       # mock upstream extracts, including deliberately overlapping/dirty records
tests/
  conftest.py                 # shared fixtures: app_base_url, autouse reset_db, session-scoped auth_headers
  ui/
    pages/                    # Page Object Model: LoginPage, DashboardPage
    test_login.py
    test_dashboard.py
  api/
    test_customers.py
    test_credit_reports.py
    test_auth.py
  etl/
    test_pipeline.py
Dockerfile                             # Jenkins LTS image + Python, for the local pipeline
Jenkinsfile                            # local Jenkins pipeline: install deps, run API+ETL suites
.github/workflows/tests.yml            # GitHub Actions: full suite on every push


## Status

- [x] Sprint 0 — repo scaffold + self-built UI/API/ETL targets
- [x] Sprint 1 — UI test suite (pytest-playwright): Page Object Model, login/form tests, dynamic-wait tests
- [x] Sprint 2 — API test suite (requests): CRUD lifecycle, schema validation, negative-path tests
- [x] Sprint 3 — ETL test suite (pandas): dedupe/threshold logic, fixtures, parametrized boundary tests
- [x] Sprint 4 — shared fixtures, GitHub Actions CI (cloud, full suite), local Jenkins CI (API+ETL), first full README
- [x] Sprint 5 — real SQLite persistence, ETL writing into the live database, full-suite test isolation via an autouse reset fixture
- [x] Sprint 6 — a second, related entity (credit reports), a genuine referential-integrity ETL rule
- [x] Sprint 7 — token-based API authentication, a safely-testable token-expiry mechanism, negative auth tests
- [x] Sprint 8 — session-based UI authentication (closing a real gap — the dashboard was previously unprotected), a live dashboard rendering real customer data
- [x] Sprint 9 — final integration pass: confirmed full-suite isolation and both CI configs already held up under everything added since Sprint 5, no gaps found; this README

**31 tests. Every line hand-typed, guided but never generated wholesale.**

## Running it

```bash
pip install -r requirements.txt
playwright install                          # one-time browser download for UI tests
ENABLE_TEST_ENDPOINTS=1 python mock_target/app.py   # serves the app on :5000 — leave running
pytest                                       # full suite (needs the app running above)
pytest -m ui                                 # UI suite only
pytest -m api                                # API suite only
pytest -m etl                                # ETL suite only — no running app needed
```

Log in with `testuser` / `Password123` on the login page to see the live
dashboard, or use the same credentials against `POST /api/login` to get a
bearer token for the API.