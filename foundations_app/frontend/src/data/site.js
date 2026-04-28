export const SITE = {
  name: "Foundations Counselling Academy",
  short: "Foundations",
  parent: "A Pameltex Group company",
  tagline: "Workplaces where people thrive — measurably.",
  email: "hello@academyfoundations.com",
  phone: "+267 71 000 000",
  address: "Plot 12345, Main Mall, Gaborone, Botswana",
  hours: "Mon – Fri · 08:00 – 17:00 CAT",
  logo: "/logo.png",
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
  "https://images.unsplash.com/photo-1522071820081-009f0129c71c?ixlib=rb-4.0.3&auto=format&fit=crop&w=2850&q=80";
export const FRAMEWORK_IMG =
  "https://images.unsplash.com/photo-1552664730-d307ca884978?ixlib=rb-4.0.3&auto=format&fit=crop&w=2940&q=80";
export const IMPACT_IMG =
  "https://images.unsplash.com/photo-1460925895917-afdab827c52f?ixlib=rb-4.0.3&auto=format&fit=crop&w=2426&q=80";

export const MOODLE_URL = "https://www.academyfoundations.com";

export const COURSES = [
  {
    slug: "mental-health-first-aid",
    title: "Mental Health First Aid for Managers",
    category: "Core Skills",
    level: "Intermediate",
    cpd: "3 CPD Points",
    duration: "4 Hours",
    modules: 4,
    accent: "#81B29A",
    summary: "Equip yourself to identify, understand, and respond to signs of mental illnesses and substance use disorders in your team.",
    outcomes: [
      "Recognize signs of distress",
      "Initiate supportive conversations",
      "Guide colleagues to professional help"
    ],
    moodlePath: "/course/view.php?id=1"
  },
  {
    slug: "psychological-safety-101",
    title: "Building Psychological Safety",
    category: "Leadership",
    level: "Advanced",
    cpd: "5 CPD Points",
    duration: "6 Hours",
    modules: 6,
    accent: "#D4A373",
    summary: "Learn how to foster an environment where employees feel safe to take risks, share ideas, and voice concerns.",
    outcomes: [
      "Measure team safety levels",
      "Design safe feedback loops",
      "Manage productive conflict"
    ],
    moodlePath: "/course/view.php?id=2"
  },
  {
    slug: "burnout-prevention",
    title: "Burnout Prevention Strategies",
    category: "Wellbeing",
    level: "Beginner",
    cpd: "2 CPD Points",
    duration: "3 Hours",
    modules: 3,
    accent: "#1C3F3A",
    summary: "Practical tools for maintaining performance while protecting personal and team wellbeing in high-pressure roles.",
    outcomes: [
      "Identify early warning signs",
      "Implement boundary-setting practices",
      "Design sustainable workflows"
    ],
    moodlePath: "/course/view.php?id=3"
  }
];
