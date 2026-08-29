# FCA Current State vs. Development Brief Mapping

**Document Date**: August 2026  
**Auditor / Architect**: Lead Product Engineer & Solutions Architect  
**Specification Reference**: Official FCA Website Update & Development Brief (August 18, 2026)  

---

## 1. Executive Direction & 4 Core Pathways

| Brief Requirement | Current Implementation | Target Implementation | Gap / Action Required |
| :--- | :--- | :--- | :--- |
| **Pathway 1: Counselling** | Covered in generic `/services/eap-counselling` and `/intake` | Dedicated `/counselling` hub with warm tone, no public pricing, 50-60 min session details, Phase 2 Gaborone, Mon-Sat hours, WhatsApp primary CTA | Create dedicated `/counselling` page; route `/services/eap-counselling` appropriately; emphasize WhatsApp book/enquire |
| **Pathway 2: Corporate Wellness & EAP** | Covered in `/services/corporate-wellness` | Dedicated `/corporate-wellness` B2B hub with EAP, ISO 45003 psychosocial risk management, leadership support, consultation form | Enhance B2B copy, add structured corporate consultation form with organization size and needs summary |
| **Pathway 3: Training & Team Building** | Covered in `/services/training` and `/learning` | Dedicated `/training-team-building` page featuring team building first, followed by accredited workshop catalog; Request Custom Quote CTA | Create `/training-team-building` highlighting experiential team building and workplace mental health |
| **Pathway 4: Online Programmes** | `/learning` and `/learning/:slug` | Retain `/learning` as FCA branded discovery layer with Kajabi outbound enrollment and UTM campaign tracking | Ensure Kajabi deep-links, 0 Moodle residuals, downloadable 7-Day Steadiness Planner teaser |

---

## 2. Navigation & Global Layout

| Requirement | Current State | Target State | Action Required |
| :--- | :--- | :--- | :--- |
| **Desktop Nav** | Home, About, Services (dropdown), Learning, Approach, Industries, Impact, Team, Contact (9 items) | Max 7 items: **Home, Counselling, Corporate, Training, Online Programmes, About, Contact** + persistent **Book / Enquire** button | Refactor `Navbar.js` to 7 streamlined items with primary header CTA |
| **Mobile Nav** | Standard sliding drawer | Floating WhatsApp quick-action (`wa.me/+267 73 860 490`) + clean hamburger drawer with safe-area spacing | Implement sticky mobile floating WhatsApp CTA and safe-area padding |
| **Footer** | Generic columns | 4 clear service columns (Counselling, Corporate, Training, Online), verified Botswana contact info, legal links | Refactor `Footer.js` to match official 4 pathways and add legal links |
| **Legal Pages** | `/privacy` only | `/privacy`, `/terms`, `/cookies`, `/disclaimer`, `/refunds` | Create `/terms`, `/cookies`, `/disclaimer`, `/refunds` legal placeholder pages |

---

## 3. Homepage Architecture

| Section | Target Requirement | Current State | Action |
| :--- | :--- | :--- | :--- |
| **Hero** | *"Practical mental wellness support for people, teams and organisations."* + *Get Support* & *Explore Corporate Services* CTAs | General brochureware hero | Update headline, sub-headline, and 2 direct conversion CTAs |
| **Pathway Cards** | 4 distinct cards immediately visible: Counselling, Corporate Wellness, Training & Team Building, Online Programmes | 3 feature highlights | Build 4 pathway cards with clear CTAs |
| **Trust Section** | Gaborone base, clinical & organisational experience, delivery formats | General stats | Add Botswana-grounded trust block without unverified BQA/HRDC claims |
| **Counselling Spotlight** | Individual & couples, confidential, warm, WhatsApp primary CTA | Mixed with general services | Build dedicated Counselling spotlight module |
| **Corporate Spotlight** | *"Healthy people. Sustainable performance."*, EAP, ISO 45003, Consultation CTA | Basic B2B card | Build high-conversion Corporate Wellness spotlight |
| **Training Spotlight** | Team building featured first, resilience, communication, quote CTA | Generic training card | Build Training spotlight with Team Building prominent |
| **Featured Online Offer** | 7-Day Steadiness Planner / Kajabi course preview (lightweight config) | Static preview | Build configurable `featured_offer` component |
| **How It Works** | 3-step friction reduction: 1. Choose support -> 2. Contact/Enrol -> 3. Begin | General process | Implement 3-step clarity flow |
| **Proof & Trust** | Approved outcomes, ethical anonymised case statements | General testimonials | Curate verified, privacy-safe social proof |
| **Closing CTA** | *"Need help choosing? Talk to FCA."* (WhatsApp, Call, Enquiry) | Basic CTA banner | Update CTABanner with direct multichannel actions |

---

## 4. Backend, Security & API Integrity

| Component | Status | Target State | Notes |
| :--- | :--- | :--- | :--- |
| **API Gateway** | Live Render FastAPI (`https://foundations-api-aq7k.onrender.com/api`) | Retain production API | Fully operational and connected |
| **Database** | MongoDB Atlas (`atlas-13zjep-shard-0`) | Retain Atlas cluster | Verified live read/write |
| **RBAC** | 4 tiers (`public`, `staff`, `admin`, `clinical_admin`, `super_admin`) | Retain RBAC | All security tests verified |
| **Clinical Isolation** | Strict segregation of `/api/clinical/intake` | Retain isolation | Aliana & CRM have zero clinical access |
| **Aliana AI** | Production assistant with prompt defense and crisis 999 response | Retain Aliana | Configured as FCA service discovery guide |
