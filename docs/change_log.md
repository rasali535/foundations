# FCA Website Upgrade Change Log

| Date | Version | Description of Changes | Affected Files | Tested By | Result |
| :--- | :--- | :--- | :--- | :--- | :---: |
| 2026-08-20 | 2.0.0 | Full production backend deployment to Render with live MongoDB Atlas connectivity | `backend/server.py`, `render.yaml`, `backend/Dockerfile` | Security/QA | **PASS (GO)** |
| 2026-08-20 | 2.1.0 | Official Website Update Brief Implementation: 4 core pathways, navigation restructuring, mobile WhatsApp CTA, dedicated service pages, legal pages, Kajabi integration | `Navbar.js`, `Footer.js`, `Home.js`, `Counselling.js`, `CorporateWellness.js`, `TrainingTeamBuilding.js`, `Resources.js`, `site.js`, `App.js` | Lead Product Eng | **PASS** |
| 2026-08-20 | 2.1.1 | Fix ReferenceError: import Counter component and support target prop in Home.js | `Home.js`, `Counter.js` | Frontend QA | **PASS** |
