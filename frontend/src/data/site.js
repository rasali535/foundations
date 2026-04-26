export const SITE = {
  name: "Foundations Counselling Academy",
  short: "Foundations",
  parent: "A Pameltex Group company",
  tagline: "Workplaces where people thrive — measurably.",
  email: "hello@foundationsca.co.bw",
  phone: "+267 71 000 000",
  address: "Plot 12345, Main Mall, Gaborone, Botswana",
  hours: "Mon – Fri · 08:00 – 17:00 CAT",
  logo: "/foundations-logo.png",
};

export const NAV = [
  { label: "Home", to: "/" },
  { label: "About", to: "/about" },
  { label: "Services", to: "/services" },
  { label: "Learning", to: "/learning" },
  { label: "Approach", to: "/approach" },
  { label: "Industries", to: "/industries" },
  { label: "Impact", to: "/impact" },
  { label: "Team", to: "/team" },
  { label: "Contact", to: "/contact" },
];

export const MOODLE_URL = "https://learn.foundationsca.co.bw";

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
    moodlePath: "/course/view.php?id=101",
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
    moodlePath: "/course/view.php?id=102",
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
    moodlePath: "/course/view.php?id=103",
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
    moodlePath: "/course/view.php?id=104",
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
    moodlePath: "/course/view.php?id=105",
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
    moodlePath: "/course/view.php?id=106",
    accent: "#D4A373",
  },
];

export const SERVICES = [
  {
    slug: "eap-counselling",
    title: "EAP & Counselling",
    category: "Responsive",
    short:
      "Confidential, evidence-based counselling and crisis support for employees and their families.",
    long:
      "We deliver a fully-managed Employee Assistance Programme covering 1:1 counselling (in-person, voice and chat), 24/7 crisis lines, trauma debriefing and proactive wellbeing campaigns. Sessions are private, ethical and outcome-tracked.",
    bullets: [
      "Short-term solution-focused counselling",
      "Critical-incident & trauma response",
      "Family & dependant access",
      "Quarterly utilisation & themes reporting",
      "Multilingual care across SADC",
    ],
    image:
      "https://images.unsplash.com/photo-1538026139293-9a46ee2a0101?crop=entropy&cs=srgb&fm=jpg&ixid=M3w4NTYxOTB8MHwxfHNlYXJjaHwxfHxwcm9mZXNzaW9uYWwlMjBtZW50YWwlMjBoZWFsdGglMjBjb3Vuc2VsbGluZyUyMHJvb218ZW58MHx8fHwxNzc3MjE2NzEwfDA&ixlib=rb-4.1.0&q=85",
  },
  {
    slug: "corporate-training",
    title: "Corporate Training",
    category: "Developmental",
    short:
      "Practical workshops that build resilient leaders, mentally fit teams and psychologically safe cultures.",
    long:
      "From mental health literacy for line managers to advanced trauma-informed leadership programmes, our training is licensed, accredited where applicable, and tailored to your operating context.",
    bullets: [
      "Mental Health First Aid (accredited)",
      "Leader resilience & burnout prevention",
      "Psychological safety for teams",
      "Difficult conversations & conflict",
      "Custom industry curricula",
    ],
    image:
      "https://images.unsplash.com/photo-1754479146459-dbba4f921949?crop=entropy&cs=srgb&fm=jpg&ixid=M3w3NDk1Nzl8MHwxfHNlYXJjaHwyfHxjbGVhbiUyMG1vZGVybiUyMGNvcnBvcmF0ZSUyMG9mZmljZSUyMGFyY2hpdGVjdHVyZXxlbnwwfHx8fDE3NzcyMTY3MTB8MA&ixlib=rb-4.1.0&q=85",
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
      "https://images.pexels.com/photos/14797777/pexels-photo-14797777.jpeg?auto=compress&cs=tinysrgb&dpr=2&h=650&w=940",
  },
  {
    slug: "organisational-development",
    title: "Organisational Development",
    category: "Developmental",
    short:
      "Culture, change and team-effectiveness work that turns wellbeing into performance.",
    long:
      "We partner on culture diagnostics, change management, leadership capability and team effectiveness — translating insight into rituals, behaviours and KPIs that stick.",
    bullets: [
      "Culture & engagement diagnostics",
      "Change management coaching",
      "Executive team effectiveness",
      "Values & behaviour design",
      "Performance & wellbeing KPIs",
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

export const INDUSTRIES = [
  {
    slug: "financial-services",
    title: "Financial Services",
    body:
      "High-pressure, regulated environments. We help reduce burnout, manage psychosocial risk and protect performance.",
  },
  {
    slug: "healthcare",
    title: "Healthcare",
    body:
      "Trauma-informed support for clinicians, debriefing, compassion-fatigue programmes and resilient rosters.",
  },
  {
    slug: "education",
    title: "Education",
    body:
      "Educator wellbeing, safeguarding training and student-facing mental health literacy.",
  },
  {
    slug: "government",
    title: "Government & Public Sector",
    body:
      "Large-scale assessments, compliance-grade reporting and culturally adapted interventions.",
  },
  {
    slug: "manufacturing",
    title: "Manufacturing & Mining",
    body:
      "Frontline-friendly EAP delivery, shift-worker resilience and incident response capability.",
  },
];

export const METRICS = [
  { value: 12, suffix: "+", label: "Years of practice" },
  { value: 150, suffix: "+", label: "Organisations supported" },
  { value: 28, suffix: "k", label: "Lives reached" },
  { value: 96, suffix: "%", label: "Client retention" },
];

export const TEAM = [
  {
    name: "Dr. Naledi Motswagole",
    role: "Principal Consultant",
    creds: "PhD Clinical Psychology · MBPsS",
    bio: "Two decades guiding executive teams across Southern Africa on workplace mental health and psychosocial risk.",
    img: "https://images.unsplash.com/photo-1758691737158-18ffa31c0a46?crop=entropy&cs=srgb&fm=jpg&ixid=M3w4NjA2MjJ8MHwxfHNlYXJjaHwyfHxkaXZlcnNlJTIwY29ycG9yYXRlJTIwdGVhbSUyMG1lZXRpbmclMjBwcm9mZXNzaW9uYWx8ZW58MHx8fHwxNzc3MjE2NzEwfDA&ixlib=rb-4.1.0&q=85",
  },
  {
    name: "Tebogo K. Selepe",
    role: "Head of Corporate Programmes",
    creds: "MSc Organisational Psychology",
    bio: "Designs leadership and culture interventions for regulated industries; previously a banking-sector HR executive.",
    img: "https://images.pexels.com/photos/8068712/pexels-photo-8068712.jpeg?auto=compress&cs=tinysrgb&dpr=2&h=650&w=940",
  },
  {
    name: "Lesego Pule",
    role: "Lead Clinician — EAP",
    creds: "MA Counselling Psychology · BAP",
    bio: "Heads our 24/7 clinical roster; specialist in trauma-focused CBT and critical-incident response.",
    img: "https://images.pexels.com/photos/14797777/pexels-photo-14797777.jpeg?auto=compress&cs=tinysrgb&dpr=2&h=650&w=940",
  },
];

export const HERO_IMG =
  "https://static.prod-images.emergentagent.com/jobs/708648c2-4bf9-4e29-9a58-36cee2a03565/images/434935005e9b2cf100a81d7923faa1ac485b0629266c0a16eeaca4b71495241e.png";
export const FRAMEWORK_IMG =
  "https://static.prod-images.emergentagent.com/jobs/708648c2-4bf9-4e29-9a58-36cee2a03565/images/2d837ab14b4a48dbfcdeb980067ccd5c47144a76e2bba9d52f9c198f093a7dfc.png";
export const IMPACT_IMG =
  "https://static.prod-images.emergentagent.com/jobs/708648c2-4bf9-4e29-9a58-36cee2a03565/images/0a398d0d81913ac14b3e0b124a42731ae7c1d5af06f34b5c9035605d7a4c4d90.png";
