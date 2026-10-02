# ---------- About you ----------
# Set this to what you can defend in an interview. It drives the "asks N+ years" penalty.
YEARS_EXPERIENCE = 4

# Strictly worldwide by default. Worldwide-only is a small, crowded slice of the market.
# Adding regions that include Nigeria widens the pool a lot, e.g. ["EMEA", "Africa", "Nigeria"]
ALSO_ACCEPT_REGIONS = []

# ---------- Volume / freshness ----------
MAX_AGE_DAYS = 14
LLM_TOP_N = 40                       # only the top N by heuristic get Claude-scored (cost control)
LLM_MODEL = "claude-haiku-4-5-20251001"

# ---------- Company boards that hire globally ----------
# Slug comes from the careers URL:
#   boards.greenhouse.io/<slug>  |  jobs.lever.co/<slug>  |  jobs.ashbyhq.com/<slug>
# Bad slugs are skipped with a log line, so experiment freely.
GREENHOUSE = []
LEVER = []
ASHBY = []

# ---------- Title rules ----------
TITLE_ROLE = r"\b(engineer|developer|swe|programmer|back[\s-]?end|full[\s-]?stack|software|platform|ai|ml|llm)\b"
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