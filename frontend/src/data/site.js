export const SITE = {
  name: "Foundations Counselling Academy",
  short: "Foundations Counselling Academy (FCA)",
  parent: "A Pameltex Group company",
  tagline: "People first. Practical support. Sustainable performance.",
  email: "info@academyfoundations.com",
  phone: "+267 72 534 203",
  whatsapp: "+267 72 534 203",
  address: "Plot 18680 Khuhurutse St, Phase 2, Gaborone, Botswana",
  hours: "Mon – Fri: 09:00 – 17:00 · Sat: 09:00 – 13:00 (Subject to confirmation)",
  logo: "/foundations-logo.png",
  canonicalUrl: "https://www.academyfoundations.com",
};

export const NAV = [
  { label: "Home", to: "/" },
  { label: "Counselling", to: "/counselling" },
  { label: "Corporate", to: "/corporate-wellness" },
  { label: "Training", to: "/training-team-building" },
  { label: "Online Programmes", to: "/learning" },
  { label: "About", to: "/about" },
  { label: "Contact", to: "/contact" },
];

export const WHATSAPP_NUMBER = "26772534203";
export const WHATSAPP_LINK = "https://wa.me/26772534203";

export const getWhatsAppUrl = (context = "general") => {
  const messages = {
    counselling: "Hello FCA, I would like to enquire about counselling.",
    corporate: "Hello FCA, I would like to enquire about corporate wellness services.",
    training: "Hello FCA, I would like to enquire about team training.",
    general: "Hello FCA, I would like to enquire about your services."
  };
  const text = encodeURIComponent(messages[context] || messages.general);
  return `https://wa.me/26772534203?text=${text}`;
};

export const KAJABI_URL = "https://academyfoundations.mykajabi.com";
export const KAJABI_LOGIN_HINT = "Direct access via FCA Kajabi Member Portal";

export const CORE_PATHWAYS = [
  {
    slug: "counselling",
    title: "Counselling",
    eyebrow: "Personal Support",
    headline: "Warm, confidential personal support.",
    description: "Individual, couples, and family therapy in-person in Gaborone or online.",
    to: "/counselling",
    cta: "Book / Enquire",
    whatsappContext: "counselling",
    accent: "#81B29A",
    audience: "Individuals, couples, parents, families"
  },
  {
    slug: "corporate-wellness",
    title: "Corporate Wellness & EAP",
    eyebrow: "Workplace Wellbeing",
    headline: "Healthy people. Sustainable performance.",
    description: "Comprehensive EAP, ISO 45003 psychosocial risk management, and crisis support.",
    to: "/corporate-wellness",
    cta: "Request Consultation",
    whatsappContext: "corporate",
    accent: "#1C3F3A",
    audience: "HR, People & Culture, Executives, Teams"
  },
  {
    slug: "training-team-building",
    title: "Training & Team Building",
    eyebrow: "Team Development",
    headline: "High-impact team building & mental wellness.",
    description: "Experiential team building, leader resilience, and workplace mental health workshops.",
    to: "/training-team-building",
    cta: "Request a Quote",
    whatsappContext: "training",
    accent: "#D4A373",
    audience: "Companies, institutions, professional teams"
  },
  {
    slug: "online-programmes",
    title: "Online Programmes",
    eyebrow: "Digital Learning",
    headline: "Self-paced CPD masterclasses & toolkits.",
    description: "Accredited masterclasses and practical workbooks hosted on our Kajabi member hub.",
    to: "/learning",
    cta: "Explore Programmes",
    whatsappContext: "general",
    accent: "#0F172A",
    audience: "Individuals, managers, professionals"
  }
];

export const FEATURED_OFFER = {
  title: "7-Day Steadiness Planner & Burnout Reset",
  description: "A practical, evidence-led digital workbook designed to help professionals recognise early burnout signals, regulate work stress, and build sustainable daily rhythms.",
  badge: "Featured Online Resource",
  kajabi_url: "https://academyfoundations.mykajabi.com",
  cta_text: "Get Free Access on Kajabi",
  active: true
};

export const COURSE_CATEGORIES = [
  "All",
  "Resilience",
  "Mental Health",
  "Leadership",
  "Communication",
];

export const COURSES = [
  {
    slug: "resilience-burnout",
    title: "Building Resilience & Preventing Burnout",
    category: "Resilience",
    level: "Foundation",
    duration: "4 weeks · self-paced",
    modules: 6,
    cpd: "8 CPD hours",
    summary:
      "Practical, evidence-based tools to recognise early-warning signs of burnout, regulate stress, and build a sustainable working rhythm.",
    outcomes: [
      "Identify your personal burnout signals",
      "Apply micro-recovery practices to your workday",
      "Set boundaries that hold under pressure",
    ],
    kajabiPath: "/products",
    accent: "#81B29A",
  },
  {
    slug: "mental-health-first-aid",
    title: "Mental Health First Aid for the Workplace",
    category: "Mental Health",
    level: "Intermediate",
    duration: "6 weeks · self-paced",
    modules: 8,
    cpd: "12 CPD hours",
    summary:
      "Equip yourself to spot, support and signpost colleagues in distress — confidently, ethically and within professional limits.",
    outcomes: [
      "Have a confident, structured supportive conversation",
      "Recognise risk and escalate appropriately",
      "Reduce stigma in your team",
    ],
    kajabiPath: "/products",
    accent: "#1C3F3A",
  },
  {
    slug: "psychological-safety-leaders",
    title: "Psychological Safety for Leaders",
    category: "Leadership",
    level: "Advanced",
    duration: "5 weeks · self-paced",
    modules: 7,
    cpd: "10 CPD hours",
    summary:
      "Move psychological safety from buzzword to operating discipline — design rituals, language and feedback loops that hold under stress.",
    outcomes: [
      "Diagnose your team's safety baseline",
      "Run candour-positive meetings",
      "Repair safety after incidents",
    ],
    kajabiPath: "/products",
    accent: "#D4A373",
  },
  {
    slug: "emotional-intelligence-work",
    title: "Emotional Intelligence at Work",
    category: "Leadership",
    level: "Foundation",
    duration: "4 weeks · self-paced",
    modules: 6,
    cpd: "8 CPD hours",
    summary:
      "Sharpen self-awareness, regulation and social skill — the four EI capabilities that separate effective leaders from competent ones.",
    outcomes: [
      "Map your EI profile honestly",
      "Use specific scripts in heated moments",
      "Coach your team's emotional habits",
    ],
    kajabiPath: "/products",
    accent: "#81B29A",
  },
  {
    slug: "difficult-conversations",
    title: "Managing Difficult Conversations",
    category: "Communication",
    level: "Intermediate",
    duration: "3 weeks · self-paced",
    modules: 5,
    cpd: "6 CPD hours",
    summary:
      "A structured, respectful approach to the conversations most people avoid — performance, behaviour, conflict and change.",
    outcomes: [
      "Open hard conversations cleanly",
      "Stay regulated when it heats up",
      "Land on shared next steps",
    ],
    kajabiPath: "/products",
    accent: "#1C3F3A",
  },
  {
    slug: "trauma-informed-leadership",
    title: "Trauma-Informed Leadership",
    category: "Leadership",
    level: "Advanced",
    duration: "6 weeks · self-paced",
    modules: 8,
    cpd: "12 CPD hours",
    summary:
      "Lead in contexts where stress, loss and adversity are part of the work — without re-traumatising your people or burning yourself out.",
    outcomes: [
      "Apply the six trauma-informed principles",
      "Design supportive operating rhythms",
      "Run trauma-aware critical incidents",
    ],
    kajabiPath: "/products",
    accent: "#D4A373",
  },
];

export const SERVICES = [
  {
    slug: "counselling",
    title: "Counselling & Psychotherapy",
    category: "Responsive",
    short:
      "Confidential, evidence-based counselling and crisis support for individuals, couples and families.",
    long:
      "We deliver compassionate, private counselling (in-person in Gaborone and virtual) covering individual therapy, couples counselling, and family support. Sessions are solution-focused, ethical and strictly confidential.",
    bullets: [
      "Individual counselling (50–60 min sessions)",
      "Couples & relationship therapy",
      "In-person in Phase 2, Gaborone & secure virtual sessions",
      "Non-emergency, solution-focused framework",
      "Confidential & professional intake onboarding",
    ],
    image:
      "https://images.unsplash.com/photo-1538026139293-9a46ee2a0101?crop=entropy&cs=srgb&fm=jpg&ixid=M3w4NTYxOTB8MHwxfHNlYXJjaHwxfHxwcm9mZXNzaW9uYWwlMjBtZW50YWwlMjBoZWFsdGglMjBjb3Vuc2VsbGluZyUyMHJvb218ZW58MHx8fHwxNzc3MjE2NzEwfDA&ixlib=rb-4.1.0&q=85",
  },
  {
    slug: "corporate-wellness",
    title: "Workplace Wellness & EAP",
    category: "Corporate",
    short:
      "Full-service Employee Assistance Programmes, 24/7 crisis support and organisational wellbeing.",
    long:
      "We partner with corporate and public sector employers to provide confidential EAP counselling, trauma debriefing, wellness days, and quarterly utilisation reporting that protects employee performance.",
    bullets: [
      "Employee Assistance Programmes (EAP)",
      "ISO 45003 psychosocial risk assessments",
      "Critical-incident debriefing & crisis response",
      "Executive & manager wellbeing coaching",
      "Quarterly aggregate utilisation reporting",
    ],
    image:
      "https://images.unsplash.com/photo-1754479146459-dbba4f921949?crop=entropy&cs=srgb&fm=jpg&ixid=M3w3NDk1Nzl8MHwxfHNlYXJjaHwyfHxjbGVhbiUyMG1vZGVybiUyMGNvcnBvcmF0ZSUyMG9mZmljZSUyMGFyY2hpdGVjdHVyZXxlbnwwfHx8fDE3NzcyMTY3MTB8MA&ixlib=rb-4.1.0&q=85",
  },
  {
    slug: "training-team-building",
    title: "Training & Team Building",
    category: "Developmental",
    short:
      "Experiential team-building retreats, resilience training, and workplace mental health workshops.",
    long:
      "We deliver high-impact, custom team building and corporate training designed to build trust, sharpen communication, resolve interpersonal friction, and elevate team performance.",
    bullets: [
      "Experiential team building & retreats",
      "Leader resilience & burnout prevention",
      "Mental health literacy for managers",
      "Managing difficult conversations & conflict",
      "Psychological safety operating rhythms",
    ],
    image:
      "https://images.pexels.com/photos/14797777/pexels-photo-14797777.jpeg?auto=compress&cs=tinysrgb&dpr=2&h=650&w=940",
  },
  {
    slug: "psychosocial-risk",
    title: "Psychosocial Risk Management",
    category: "Preventative",
    short:
      "ISO 45003 aligned assessments that surface, quantify and reduce psychosocial hazards at work.",
    long:
      "We map exposure across job demands, role clarity, leadership, recognition and relationships, then deliver a prioritised mitigation plan with executive-ready dashboards.",
    bullets: [
      "ISO 45003 baseline assessment",
      "Hazard identification & control plans",
      "Board-level risk dashboards",
      "Compliance & audit support",
      "Annual re-measurement",
    ],
    image:
      "https://images.pexels.com/photos/8068712/pexels-photo-8068712.jpeg?auto=compress&cs=tinysrgb&dpr=2&h=650&w=940",
  },
];

export const PILLARS = [
  {
    n: "01",
    title: "Assessment",
    body:
      "Quantitative and qualitative diagnostics — surveys, interviews, ISO 45003 mapping — to surface what's really happening.",
  },
  {
    n: "02",
    title: "Intervention",
    body:
      "Targeted programmes from EAP and clinical care to leadership coaching and culture redesign.",
  },
  {
    n: "03",
    title: "Reinforcement",
    body:
      "Embedding new behaviours via toolkits, manager rituals, peer-support networks and ongoing coaching.",
  },
  {
    n: "04",
    title: "Reporting",
    body:
      "Board-ready dashboards covering utilisation, risk, ROI and compliance — so impact is visible.",
  },
];

export const HOW_IT_WORKS_STEPS = [
  {
    step: "01",
    title: "Choose your support",
    description: "Identify whether you need individual counselling, corporate EAP wellness, team training, or online CPD programmes."
  },
  {
    step: "02",
    title: "Contact FCA or enrol",
    description: "Reach out via WhatsApp or phone for counselling, request a corporate consultation, or enrol directly in Kajabi masterclasses."
  },
  {
    step: "03",
    title: "Begin your practical next step",
    description: "Confirm session availability, receive your tailored proposal, or start learning at your own pace immediately."
  }
];

export const TEAM = [
  {
    name: "Caroline Sithole",
    role: "Principal Counsellor",
    creds: "MSc · BSc · PSY",
    bio: "Senior facilitator and board-certified counsellor specialising in Cognitive Behavioral Therapy (CBT); leads the academy's corporate resilience and wellness workshops.",
    img: "/caroline.jpg",
  },
  {
    name: "Thamu X Gordon Mthupa",
    role: "Lead Counselor",
    creds: "",
    bio: "Heads clinical training and counseling programmes, bringing extensive expertise in trauma-informed curriculum design and regional EAP supervision.",
    img: "/thamu.jpg",
  },
  {
    name: "Alpheaus Chiwaze",
    role: "Head of Operations",
    creds: "",
    bio: "Heads operations and digital learning systems, managing the academy's online course delivery infrastructure and educational technologies.",
    img: "/alpheaus.jpg",
  },
  {
    name: "Ms. Sithembinkosi Rutendo Mthupa",
    role: "Client Services Director",
    creds: "MBA · BCom Management",
    bio: "Manages strategic partnerships, corporate client enrollment, and service delivery frameworks across our regional portfolio.",
    img: "/team-mthupa.jpg",
  },
];

export const METRICS = [
  { value: 12, suffix: "+", label: "Years of practice" },
  { value: 150, suffix: "+", label: "Organisations supported" },
  { value: 28, suffix: "k", label: "Lives reached" },
  { value: 96, suffix: "%", label: "Client retention" },
];

export const INDUSTRIES = [
  {
    slug: "financial-services",
    title: "Financial Services",
    body: "High-pressure, regulated environments. We help reduce burnout, manage psychosocial risk and protect performance.",
  },
  {
    slug: "healthcare",
    title: "Healthcare",
    body: "Trauma-informed support for clinicians, debriefing, compassion-fatigue programmes and resilient rosters.",
  },
  {
    slug: "education",
    title: "Education",
    body: "Educator wellbeing, safeguarding training and student-facing mental health literacy.",
  },
  {
    slug: "government",
    title: "Government & Public Sector",
    body: "Large-scale assessments, compliance-grade reporting and culturally adapted interventions.",
  },
  {
    slug: "manufacturing",
    title: "Manufacturing & Mining",
    body: "Frontline-friendly EAP delivery, shift-worker resilience and incident response capability.",
  },
];

export const HERO_IMG =
  "https://images.unsplash.com/photo-1522071820081-009f0129c71c?ixlib=rb-4.0.3&auto=format&fit=crop&w=2850&q=80";
export const FRAMEWORK_IMG =
  "https://images.unsplash.com/photo-1552664730-d307ca884978?ixlib=rb-4.0.3&auto=format&fit=crop&w=2940&q=80";
export const IMPACT_IMG =
  "https://images.unsplash.com/photo-1460925895917-afdab827c52f?ixlib=rb-4.0.3&auto=format&fit=crop&w=2426&q=80";

export const RESOURCES_LIST = [
  {
    slug: "steadiness-planner",
    title: "7-Day Steadiness Planner",
    type: "Downloadable PDF Workbook",
    description: "Evidence-led daily exercises to recognise burnout triggers, regulate stress, and build calm momentum.",
    link: "https://academyfoundations.mykajabi.com",
    badge: "Free Tool"
  },
  {
    slug: "psychosocial-risk-checklist",
    title: "ISO 45003 Workplace Risk Checklist",
    type: "Executive Guide",
    description: "A quick-audit checklist for HR and business leaders to identify top psychosocial hazards in team operations.",
    link: "/corporate-wellness",
    badge: "B2B Guide"
  },
  {
    slug: "mental-health-conversation-guide",
    title: "Line Manager Supportive Conversation Guide",
    type: "Practical Script & Framework",
    description: "How to open and manage supportive 1:1 conversations with a team member in distress ethically and effectively.",
    link: "/training-team-building",
    badge: "Manager Script"
  }
];

