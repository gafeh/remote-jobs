# ---------- About you ----------
YEARS_EXPERIENCE = 4  # set to what you can defend in an interview

# Remote roles open to these regions are accepted alongside true worldwide roles.
ALSO_ACCEPT_REGIONS = ["EMEA", "MEA", "Africa", "Sub-Saharan Africa", "West Africa", "Nigeria", "Lagos"]

# Include on-site/hybrid roles anywhere IF the posting explicitly offers visa sponsorship.
INCLUDE_VISA_SPONSORED = True

# ---------- Volume / freshness ----------
MAX_AGE_DAYS = 14
SOURCE_MAX_AGE_DAYS = {"HN Who's Hiring": 35}  # monthly thread, so allow a longer window
LLM_TOP_N = 50
LLM_MODEL = "claude-haiku-4-5-20251001"

# ---------- Morning digest (optional, needs SMTP secrets) ----------
DIGEST_MIN_SCORE = 60

# ---------- Company boards (slugs verified live, Oct 2026) ----------
# Chosen because their boards actually carry Worldwide / EMEA / Global / "Any Location" roles.
GREENHOUSE = [
    "canonical",          # "Home based - Worldwide" and "Home based - EMEA"
    "automatticcareers",  # Automattic, fully distributed
    "wikimedia",
    "sourcegraph91",      # Sourcegraph
    "netlify",
    "mozilla",
    "gitlab",
    "consensys",          # many "EMEA - Remote" roles
    "okx",                # some EMEA roles
    "elastic",            # occasional EMEA roles + explicit sponsorship language
    "labelbox",
]
LEVER = []  # none of the Lever boards tested carried global-remote roles; add your own
ASHBY = [
    "supabase",   # "Remote, Global"
    "posthog",
    "railway",    # "Global"
    "oyster",     # "EMEA", "Any Location"
    "zapier",
    "clerk",
    "braintrust",
]

# Boards whose bare "Remote" location really means "anywhere". Description blockers still apply.
TRUST_BARE_REMOTE = {"automatticcareers", "wikimedia", "sourcegraph91", "posthog"}

# ---------- Title rules ----------
TITLE_ROLE = r"\b(engineer|engineers|engineering|developer|developers|swe|programmer|back[\s-]?end|full[\s-]?stack|software|platform|ai|ml|llm)\b"
TITLE_REJECT = (
    r"\b(staff|principal|distinguished|director|vp|vice president|head of|manager|architect|intern|"
    r"sales|marketing|recruiter|designer|ios|android|salesforce|sap|qa|test|support|"
    r"trainer|annotator|tutor|writer|rater)\b"
)

# ---------- Your skills: (label, regex, weight) ----------
SKILLS = [
    ("Python", r"python", 3),
    ("TypeScript", r"typescript", 3),
    ("Node.js", r"node(\.?js)?", 3),
    ("PostgreSQL", r"postgres(ql)?", 3),
    ("Backend", r"back[\s-]?end", 3),
    ("LLM", r"llms?|large language models?", 3),
    ("FastAPI", r"fastapi", 2),
    ("Django", r"django", 2),
    ("GraphQL", r"graphql", 2),
    ("Prisma", r"prisma", 2),
    ("AWS", r"aws|amazon web services", 2),
    ("RAG", r"rag|retrieval[\s-]augmented", 2),
    ("Evals", r"evals?|evaluations?", 2),
    ("Agents", r"agentic|ai agents?|llm agents?", 2),
    ("pgvector", r"pgvector|vector (db|database)s?", 2),
    ("Payments", r"stripe|payments?", 2),
    ("Full stack", r"full[\s-]?stack", 2),
    ("Express", r"express(\.js)?", 1),
    ("REST", r"rest(ful)?\s+apis?", 1),
    ("Docker", r"docker", 1),
    ("Kubernetes", r"kubernetes|k8s", 1),
    ("Terraform", r"terraform", 1),
    ("Redis", r"redis", 1),
    ("React", r"react", 1),
    ("Next.js", r"next\.?js", 1),
    ("Queues", r"queues?|background jobs", 1),
]
SKILL_CAP = 30