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