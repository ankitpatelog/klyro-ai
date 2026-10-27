### Design System Rules & Color Palette
- **Primary Accent:** `#8172d8` (Hover: `#6658bb`, Light container/bg: `#ece8ff`, Border/Focus accent: `#d6cffa`)
- **Backgrounds:** 
  - Main app background: Default/transparent section container (`min-w-0`)
  - Cards & Modals: `#ffffff` or `#fffefa` with rounded corners (`rounded-2xl` or `rounded-3xl`)
  - Modal overlay: `#273045`/35 with backdrop blur (`backdrop-blur-[3px]`)
- **Text Colors:**
  - Headings & primary labels: `#273045`
  - Body & secondary text: `#6d7484`
  - Subdued / Placeholders: `#a4a49b`
  - Overline / Eyebrow text: 10px font-semibold tracking-[0.22em] text-[#8172d8] UPPERCASE
- **Borders & Dividers:** `#e8e5de` (Light borders), `#d9d6d0` (Input borders)
- **Status Colors:**
  - Running / Success: `#137333` text, `#e6f4ea` background, `#34a853` pulse dot
  - Stopped / Error: `#b3261e` text, `#fce8e6` background, `#ea4335` dot
- **Shadows & Effects:** 
  - Standard Card Shadow: `shadow-sm` with hover glow `shadow-[0_12px_35px_#8172d81a]`
  - Transitions: `transition duration-200 hover:-translate-y-0.5`
- **Buttons & Inputs:**
  - Primary button: `rounded-xl bg-[#8172d8] px-5 py-3 text-sm font-medium text-white transition hover:bg-[#6658bb]`
  - Inputs/Search: `h-10 rounded-xl border border-[#e8e5de] bg-white px-3 outline-none`



Implement 6 core features. That is enough to make the project feel production-ready without becoming over-engineered.
Contextual chunking with metadata
Better chunks improve retrieval quality and reduce irrelevant tokens.

Hybrid retrieval + reranking
Combines semantic and keyword search, then selects only the best sources for the final prompt.

Token-budget manager
Caps context sent to the model and prioritizes the most relevant chunks. This is the clearest token-optimization feature.

Conversation memory summarization
Summarizes older chat messages instead of sending the whole conversation every time.

Semantic cache
Reuses answers for repeated or very similar questions, cutting latency and LLM cost.

Observability dashboard
Track tokens, cost, latency, cache-hit rate, retrieved chunks, and model used. This proves the optimizations actually work.

Why these six: together they cover the complete RAG lifecycle—document preparation, retrieval quality, prompt-size control, chat scalability, cost reduction, and measurable results. That is excellent material for an interview.



cd D:\klyro-ai\backend
.\kyro\Scripts\python.exe -m app.workers.embedding_worker

.\kyro\scripts\activate

uvicorn app.main:app --reload



cd D:\klyro-ai\backend
.\kyro\Scripts\activate
uvicorn app.main:app --reload



























# NEON DATABASE
NEON_DATABASE_PASS=npg_Gfq0XIxpAVM7
DATABASE_URL='postgresql://neondb_owner:npg_Gfq0XIxpAVM7@ep-soft-mouse-b5ekoo6r-pooler.c-7.us-east-2.aws.neon.tech/neondb?sslmode=require&channel_binding=require'


# S3-compatible storage. Generate a credential to fill in the key ID + secret.
AWS_ENDPOINT_URL_S3="https://br-twilight-fire-b54e3btu.storage.c-7.us-east-2.aws.neon.tech"
AWS_ACCESS_KEY_ID="nak_live_311259e126894b14a05061324f664d47"
AWS_SECRET_ACCESS_KEY="nsk_live_05154ef7f64a642575368df9dda151c702e866e130814ac1969b381cb0c439b0"
AWS_REGION="us-east-2"

# jwt secret key
JWT_SECRET_KEY=abcdefghijklmnopqrstuvwxyzkdkeir6788fjhgjh976hjhghj
ACCESS_TOKEN_EXPIRE_MINUTES=4000
REFRESH_TOKEN_EXPIRE_DAYS=30
JWT_ALGORITHM=HS256


# redis
REDIS_URL=redis://default:hQKYh7lcPpebTE0izgjOiMuErsTWi9uX@redis-10777.c62.us-east-1-4.ec2.cloud.redislabs.com:10777
COOKIE_SECURE=false
COOKIE_SAMESITE=lax
CORS_ORIGINS=http://localhost:3000

# supabase 
SUPABASE_URL=postgresql://postgres:EUlBa6Yii5hpC1LK@db.ibdghkqzensuzdsdxwux.supabase.co:5432/postgres
SUPABASE_SERVICE_ROLE_KEY=sb_secret_VzwId0l5eShxV38OHelxdw_yTsJDIso
# SUPABASE_SERVICE_ROLE_KEY=sb_secret_VZsg_DHE9_00Fg8ENMXz1Q_ODfDok_o
SUPABASE_STORAGE_BUCKET=kyroai-knowledge-base


# qdrant 
QDRANT_URL=https://b20592f7-3010-4d63-bb88-382e2e4e47fa.sa-east-1-0.aws.cloud.qdrant.io
QDRANT_COLLECTION=klyro-ai
QDRANT_API_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJhY2Nlc3MiOiJtIiwic3ViamVjdCI6ImFwaS1rZXk6ZjZiZGM2ZDQtZDBiNS00ZWExLWFkZjItZTk5ZmZkZGMyMTgwIn0.EoaZYRFnP7EXqNthDHjjTlSY1xSSS3JV37cUc9DlNd4

# jina embeddings
EMBEDDING_API_URL=https://api.jina.ai/v1
EMBEDDING_API_KEY=jina_4e8c8e4c8b08404a9c9ee145692a762bUPMHMnu6RJLbEdsDdiGbRBtsvBg4

# Recommended for text knowledge bases:
EMBEDDING_MODEL=jina-embeddings-v5-omni-small
EMBEDDING_DIMENSIONS=1024


# groq open api key
GROQ_API_KEY=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
GENERATION_API_URL=https://api.groq.com/openai/v1
GENERATION_MODEL=openai/gpt-oss-120b

# 
RAG_USER_REQUESTS_PER_MINUTE=10
RAG_GENERATION_MAX_RETRIES=2
RAG_CIRCUIT_BREAKER_SECONDS=30


NVIDIA_API_KEY=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
NEMO_GUARDRAILS_ENABLED=false
NEMO_GUARDRAILS_CONFIG_PATH=app/guardrails


# smtp email
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=ankitpatel22092004@gmail.com
SMTP_PASSWORD=dtsd snrg zaol ygyf
SMTP_FROM_EMAIL=ankitpatel22092004@gmail.com
SMTP_FROM_NAME=Klyro AI
SMTP_USE_TLS=true
EMAIL_VERIFICATION_TTL_SECONDS=600
