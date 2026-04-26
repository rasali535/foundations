# Foundations Counselling Academy — Multi-Page Website

## Original Problem Statement
A modern, sleek, multi-page corporate website for **Foundations Counselling Academy** (a Pameltex Group company in Botswana) — a workplace mental health and organisational development consultancy. The site must present the company as a leading psychosocial-risk and EAP partner for HR teams, executives, procurement and government stakeholders, with motion graphics, refined animations, and an integrated AI chatbot to drive enquiries and strengthen brand trust.

## User Personas
- HR managers and People & Culture teams
- Business owners and executive leaders
- Procurement / corporate decision-makers
- Government and institutional stakeholders
- Sectors: Financial services, Healthcare, Education, Government, Manufacturing

## Architecture
- **Frontend**: React 19 + React Router 7 + Tailwind + framer-motion + shadcn-ui + lucide-react
- **Backend**: FastAPI + Motor (MongoDB)
- **AI Chatbot**: GPT-5.2 via `emergentintegrations.llm.chat.LlmChat` using `EMERGENT_LLM_KEY`
- **Database**: MongoDB collections — `contact_submissions`, `chatbot_leads`, `chat_messages`
- **Routing**: 11 routes (Home, About, Services, 4 Service detail pages, Approach, Industries, Impact, Team, Contact, Privacy, 404)

## Core Requirements (static)
1. Multi-page responsive site with sleek calm premium corporate palette (deep forest #1C3F3A + ivory + warm tan accent)
2. Premium animated homepage hero, scroll-reveals, animated counters, smooth page transitions
3. Floating AI chatbot (Aria) — answers service questions, captures leads (name/company/email/phone/inquiry)
4. Contact form storing submissions in MongoDB
5. Service categorisation (Preventative / Responsive / Developmental)
6. Reusable content components (hero, section heading, service cards, pillar cards, industry tiles, team cards, CTA banner, contact form, chatbot widget)
7. Privacy policy page

## What's Been Implemented (Feb 2026 — Initial MVP)
- ✅ Backend API: `/api/`, `/api/contact` (POST/GET), `/api/chat/message` (GPT-5.2), `/api/chat/history/{session_id}`, `/api/chat/lead` (POST/GET), `/api/chat/leads`
- ✅ MongoDB persistence with `_id` excluded, ISO-string timestamps
- ✅ EMERGENT_LLM_KEY wired into backend `.env`
- ✅ Custom system prompt for Aria persona scoped to FCA services & lead capture
- ✅ Frontend: 11 routes wired via React Router with page transitions
- ✅ Animated hero (HERO_IMG abstract organic shapes), staggered entrance, glassmorphism credibility card
- ✅ Animated metric counters (4 metrics — years, organisations, lives reached, retention)
- ✅ 4 services with separate detail pages and slug routing (eap-counselling, corporate-training, psychosocial-risk, organisational-development)
- ✅ Four Pillars Framework page with alternating bento layout
- ✅ Industries page (5 sectors)
- ✅ Impact / Capability Statement with 3 capability categories
- ✅ Team page with 3 placeholder bios
- ✅ Contact page with form + sonner toasts + success state
- ✅ Privacy Policy
- ✅ Floating chatbot with chat / lead-form / done states, spring-animated open, message microinteractions
- ✅ Global Navbar (sticky glassmorphism) and dark green Footer
- ✅ All interactive elements have `data-testid` attributes
- ✅ Tested end-to-end (backend pytest 6/6 passing; frontend 13 routes load, chatbot LLM works, contact form submits)

## Backlog / Next Action Items
**P1 (high-value, deferred):**
- Real brand assets (logo SVG, real team photos, final principal-consultant credentials) once user supplies them
- Email notification on contact + lead capture (user said they'll handle via PHP — needs webhook target)
- Admin dashboard to view submissions / leads / chat sessions

**P2 (nice-to-have):**
- Blog / Insights section
- Downloadable Capability Statement PDF
- Testimonials & case studies section
- Consultation booking integration (calendar)
- Sitemap + SEO meta tags per page (currently default)
- Cookie banner aligned with Privacy Policy
- i18n (Setswana + English)

**P3 (operational):**
- Pagination for `/api/contact` and `/api/chat/leads` (currently caps at 500)
- Rollback of orphan `chat_messages.user` row on LLM failure
- Surface chatbot lead-submit error toast (currently silent)
