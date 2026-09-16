# Python + PyTest Testing Portfolio
![Tests](https://github.com/ganeshkumar-chelladurai-sdet/python-testing-portfolio/actions/workflows/tests.yml/badge.svg)
A single self-contained project demonstrating UI, API, and ETL/data-pipeline
testing with **Python and PyTest only** — built to close a specific gap:
Python/PyTest keeps showing up across QA/SDET job descriptions in Ireland,
separately from the Java/Selenium framework in my other repo.

## Why a self-built system under test

Rather than testing third-party public sites, this repo includes its own
small system under test (`mock_target/`) — a Flask app with a login page
and a customers API, plus a CSV-based ETL pipeline with a dedupe and
credit-score threshold validation step. That ETL logic mirrors real work
from my time at Cognizant (ETL/data pipeline validation, ~99% data
integrity) and TransUnion (regression coverage across UI/API/ETL) —
translated out of the enterprise ETL GUI (Ab Initio / Express>It) I used
on the job, into plain pandas + PyTest, so the reasoning is visible and
testable on its own.

## Structure

```
mock_target/
  app.py              # Flask app: login page (UI target) + /api/customers (API target)
  templates/login.html
  etl/pipeline.py      # ETL target: load -> merge -> dedupe -> threshold validate
  data/                # mock upstream extracts with overlapping/dirty records
tests/
  ui/    # pytest-playwright tests against the login page
  api/   # pytest + requests tests against /api/customers
  etl/   # pytest + pandas tests against pipeline.py functions
```

## Status

- [x] Sprint 0 — repo scaffold + self-built UI/API/ETL targets
- [ ] Sprint 1 — UI test suite (pytest-playwright)
- [ ] Sprint 2 — API test suite (requests)
- [ ] Sprint 3 — ETL test suite (pandas) — priority, ties directly to a specific
      interview feedback point on demonstrating data-validation reasoning
      independent of an enterprise ETL GUI
- [ ] Sprint 4 — shared fixtures, GitHub Actions CI, final docs

## Running it

```bash
pip install -r requirements.txt
python mock_target/app.py          # serves the UI/API target on :5000
python mock_target/etl/pipeline.py # runs the ETL pipeline standalone
pytest                             # once test suites are written
```
