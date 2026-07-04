# Cómo funcionan los libros como insumo — Arquitectura profunda

Sistema RAG (Retrieval-Augmented Generation) + Knowledge Graph que convierte libros de
teoría de guion en conocimiento estructurado, y lo inyecta en la generación y el review
de guiones vía agentes especializados.

Dos mitades:
- **INGESTA** (offline, una vez por libro): libro → texto → chunks+embeddings → knowledge graph (conceptos, relaciones, snippets) → todo vectorizado.
- **CONSUMO** (online, en cada review/chat): texto de guion + sección → retrieval (semántico/por-sección) → inyección en prompt → respuesta IA con citas al libro.

---

## 1. Vista de 10.000 pies

```
┌──────────────────────────── INGESTA (una vez por libro) ────────────────────────────┐
│                                                                                       │
│  📄 Libro          📝 Texto         ✂️ Chunks         🧠 Knowledge Graph (GPT-4)      │
│  PDF/EPUB/TXT  →   por página   →   750 tok        →   Conceptos ─┬─ Relaciones       │
│  (≤50MB)           /capítulo        (overlap 150)      Snippets    │  (depends_on,     │
│                                          │             (texto       │   related_to...)  │
│                                          ▼             exacto)      │                   │
│                                     🔢 Embeddings (OpenAI text-embedding-3-small, 1536D)│
│                                          │                                              │
│                                          ▼                                              │
│                          🗄️  Postgres + pgvector                                       │
│                          books · book_chunks · concepts · concept_relationships ·       │
│                          snippets   (todos con columna embedding vector(1536))          │
└───────────────────────────────────────────┬───────────────────────────────────────────┘
                                             │
                       🤖 Agent ──(agent_books M2M)── 📚 Books
                       (BOOK_BASED / TAG_BASED / ORCHESTRATOR)
                                             │
┌────────────────────────────── CONSUMO (cada review/chat) ─┴──────────────────────────┐
│                                                                                        │
│  ✍️ Sección de guion        🔍 Retrieval (rag_service)         💉 Prompt + 🧠 IA       │
│  (texto + section_type)  →  ┌─ por-sección (review)        →   system prompt con       │
│                            │  section_relevance[SECTION]       concept cards +          │
│                            └─ semántico (chat)                 chunks + relaciones      │
│                               query→embed→ <=> cosine          + texto del guion        │
│                                          │                          │                   │
│                                          ▼                          ▼                   │
│                                    top conceptos/chunks    OpenAI/Anthropic            │
│                                                                    │                    │
│                                                                    ▼                    │
│                                         💬 Respuesta con book_references (citas) +      │
│                                            field_updates / list_item_creates            │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. INGESTA — paso a paso (background, async)

Disparador: `POST /api/books/upload` → `books.py:44 upload_book()` valida (PDF/EPUB/TXT, ≤`MAX_BOOK_SIZE_MB`=50), guarda en `UPLOAD_DIR/{user_id}/`, crea `Book(status=PENDING)` y lanza `BackgroundTasks` → `book_processing_service.process_book()`.

Orquestador: `book_processing_service.py:32 process_book()`. Estados en `Book.status` (enum `BookStatus`): `PENDING → EXTRACTING → EMBEDDING → ANALYZING → EMBEDDING → COMPLETED` (o `PAUSED`/`FAILED`). `Book.progress` 0→100, con checkpoint por capítulo (`chapters_processed`) que permite **pause/resume/retry**.

```
process_book(book_id, file_path, db, start_chapter=0)
│
├─ STEP 1  EXTRACTING                          document_service.py:69 extract_text()
│   PDF→PyPDF2 · EPUB→ebooklib+BS4 · TXT       → List[{text, page_number|chapter_title}]   (progress 5)
│
├─ STEP 2  EMBEDDING (chunks)                  document_service.py:85 chunk_text()
│   tiktoken gpt-4, ventana deslizante         CHUNK_SIZE_TOKENS=750, OVERLAP=150
│   embedding_service.py:41 embed_batch()       OpenAI text-embedding-3-small → 1536D, batch=50,
│                                               backoff exponencial ante RateLimitError
│   → persiste BookChunk(content, token_count, embedding, chapter_title, page_number)   (progress 10)
│
├─ STEP 3  ANALYZING (Knowledge Graph, por capítulo)   document_service.py:136 split_into_chapters()
│   loop capítulo → knowledge_extraction_service.py:258 process_chapter()  (GPT-4, json_mode, temp 0.3)
│     ├─ Stage 1  extract_concepts()       3-8 conceptos: name, definition, page_range, tags, quality_score
│     ├─ Stage 2  analyze_concept() x N    examples (películas), actionable_questions,
│     │                                     section_relevance {INCITING_INCIDENT:0.8, MIDPOINT:0.3, ...}
│     ├─ Stage 3  extract_relationships()  depends_on · related_to · part_of · example_of · contradicts · extends
│     └─ Stage 4  extract_snippets()       3-5 citas TEXTUALES exactas (50-300 palabras) + justification
│   progress = 10 + 75 * (chapters_processed / chapters_total)
│   asyncio.CancelledError → PAUSED (checkpoint en chapters_processed)
│
├─ QUALITY FILTER     descarta conceptos con quality_score < 0.5
│
├─ STEP 4  EMBEDDING (conceptos)   embed_batch(definitions) → persiste Concept(... embedding 1536D)  (progress 90)
├─ STEP 5  Relaciones             persiste ConceptRelationship(source_id, target_id, relationship, description)
├─ STEP 6  EMBEDDING (snippets)   embed_batch(snippet_texts) → persiste Snippet(content, concept_ids[], embedding)
├─ STEP 7  Link chunks↔conceptos  si nombre de concepto ∈ texto del chunk → chunk.concept_ids += concept.id
└─ STEP 8  COMPLETED              total_concepts, processed_at, progress=100
```

Controles de ciclo de vida (todos en `books.py` → delegan a `book_processing_service`):
- `pause` → cancela `_active_tasks[book_id]` (registry global de `asyncio.Task`)
- `resume` → reanuda en `start_chapter = book.chapters_processed`
- `retry` → borra chunks(no user)/concepts/snippets y reprocesa desde 0
- `delete` → cascade borra chunks/concepts/snippets + archivo en disco

---

## 3. Modelo de datos (Postgres + pgvector)

```
users
  └─< books (owner_id)                                    [status, progress, chapters_*]
        ├─< book_chunks      (book_id)   embedding vector(1536)  concept_ids JSON[]  ← RAG citations
        ├─< concepts         (book_id)   embedding vector(1536)  section_relevance JSON  quality_score
        │     ├─< concept_relationships (source_concept_id, target_concept_id, relationship enum)
        │     └─  (examples, actionable_questions, tags) JSON
        ├─< snippets         (book_id)   embedding vector(1536)  concept_ids/names JSON[]  ← citas textuales
        └─<>  agents   vía  agent_books (agent_id, book_id)   ← qué agente "lee" qué libros

agents  [agent_type: BOOK_BASED | TAG_BASED | ORCHESTRATOR · tags_filter JSON · system_prompt_template]
agent_pipeline_maps  [agent_id → phase + subsection_key + confidence]   ← compuesto por pipeline_composer
```

Tipo custom `SafeVector(1536)` (`database.py:12`) — adapta la columna pgvector a psycopg2/psycopg3.
La columna `embedding` está **deferred** (no se carga salvo que se pida) para no traer 1536 floats en cada query.

Las **3 capas de granularidad** del conocimiento de un libro:
| Capa | Tabla | Para qué se usa |
|------|-------|-----------------|
| Grueso (RAG bruto) | `book_chunks` | Excerpts crudos como evidencia/citas |
| Estructurado | `concepts` (+`concept_relationships`) | Reviews por sección, knowledge graph |
| Curado | `snippets` | Citas textuales de alta señal por concepto |

---

## 4. CONSUMO — dado (texto de guion + sección), ¿cómo entra el libro al prompt?

Dos modos de retrieval según el caso de uso:

### Modo A — Review estructurado por sección (concept-first)
`chat.py POST /sessions/{id}/review` → `agent_service.py:276 review_section()`

```
review_section(section_text, section_type, agent, db)
│
├─ BOOK_BASED  → rag_service.py:26 get_relevant_concepts(section_type, agent_id, top_k=MAX_CONCEPTS_PER_REVIEW=10)
│     concepts WHERE book_id IN (SELECT book_id FROM agent_books WHERE agent_id=:id)
│     ORDER BY  concept.section_relevance[SECTION_TYPE]  DESC      ← clave: relevancia por sección
│  ├─ rag_service.py:80  get_concept_relationships(concept_ids)
│  └─ rag_service.py:112 get_supporting_chunks(concept_ids, top_k=4)
│        book_chunks WHERE concept_ids ?| :concept_ids            ← JSONB array overlap
│
├─ TAG_BASED   → get_concepts_by_tags(tags_filter, owner_id) + filtro section_relevance
│
├─ _build_system_prompt(concepts, relationships, chunks, framework, section_type, project_context)
│     _format_concept_cards()  → name, definition, fuente(cap+pág), ejemplos película, actionable_questions
│     _format_chunks()         → excerpts (≤800 chars) con [book, Ch, p.N]
│     _format_relationships()  → source → tipo → target: desc
│     → inyecta en agent.system_prompt_template
│
├─ chat_completion(system=prompt_con_contexto, user=section_text, json_mode=True)   (OpenAI/Anthropic)
└─ → {issues, suggestions, book_references[top5]} → guarda ChatMessage(role=review, concepts_used)
```

### Modo B — Chat semántico (query-first, vectorial)
`chat.py POST /sessions/{id}/messages[/stream]` → `agent_service.py:384 chat()` / `:527 chat_stream_prepare()`

```
chat(user_query, agent, db)
│
├─ embedding_service.embed_text(user_query)                       → vector 1536D
├─ rag_service.py:164 semantic_search(embedding, agent_id|tags)
│     SELECT ..., 1 - (c.embedding <=> CAST(:emb AS vector)) AS similarity     ← pgvector cosine
│     FROM concepts c [JOIN agent_books | WHERE tags ?| :tags]
│     ORDER BY c.embedding <=> :emb  LIMIT top_k
│     (+ chunks análogos)
│
├─ system_prompt += "## Relevant Concepts" + "## Supporting Book Excerpts"
├─ chat_completion(messages, json_mode)   → texto + {book_references} + {field_updates|list_item_creates}
└─ guarda ChatMessage(content, book_references, concepts_used)
```

### Modo C — Orchestrator (multi-agente)
`agent_service.py:852 _orchestrate()` cuando el agente es `ORCHESTRATOR`:
1. `_select_relevant_agents()` — embeddea el query, puntúa cada agente por **máxima similitud** de sus conceptos (`_score_agent_book_based` / `_score_agent_tag_based`), toma **top 3** (`MAX_AGENTS_PER_REVIEW=5`).
2. Por agente: `_get_specialist_context()` → `semantic_search()` (top 4 conceptos, 2 chunks) en paralelo.
3. Agrega todo y arma un **prompt de síntesis** → una respuesta unificada con `consulted_agents`.

---

## 5. El "secreto" del matching por sección

Lo que hace que esto sea más que un RAG genérico: durante la ingesta, `analyze_concept()` (Stage 2)
le pide a GPT-4 que puntúe **qué tan relevante es cada concepto para cada sección narrativa**
(`section_relevance: {INCITING_INCIDENT: 0.9, PLOT_POINT_1: 0.4, MIDPOINT: 0.2, ...}`).

Así, en el review de, por ejemplo, el `MIDPOINT`, `get_relevant_concepts()` no busca por similitud de
texto sino que **ordena los conceptos del libro por su `section_relevance[MIDPOINT]`** — trae justo la
teoría que aplica a ese beat estructural. El retrieval vectorial (`<=>` cosine) se reserva para el chat
libre, donde el query del usuario es la consulta.

---

## 6. Parámetros (config.py)

| Parámetro | Valor | Rol |
|-----------|-------|-----|
| `EMBEDDING_MODEL` / `EMBEDDING_DIMENSION` | text-embedding-3-small / 1536 | vectores |
| `MAX_BOOK_SIZE_MB` | 50 | límite upload |
| `CHUNK_SIZE_TOKENS` / `CHUNK_OVERLAP_TOKENS` | 750 / 150 | chunking |
| `KG_EXTRACTION_MODEL` | gpt-4 | extracción knowledge graph |
| `MAX_CHUNKS_PER_RETRIEVAL` | 6 | tope chunks recuperados |
| `MAX_CONCEPTS_PER_REVIEW` | 10 | tope conceptos por review |
| `MAX_AGENTS_PER_REVIEW` | 5 | tope agentes (orchestrator) |
| `AGENT_RELEVANCE_THRESHOLD` | 0.3 | umbral selección de agente |
| `PIPELINE_BATCH_SIZE` / `PIPELINE_COMPOSITION_MAX_TOKENS` | 5 / 2000 | composición de pipeline |
| quality threshold (hardcoded) | 0.5 | descarta conceptos pobres |

---

## 7. Archivos clave

| Capa | Archivo |
|------|---------|
| Endpoints upload/estado | `backend/app/api/endpoints/books.py` |
| Orquestador ingesta | `backend/app/services/book_processing_service.py` |
| Extracción texto/chunking | `backend/app/services/document_service.py` |
| Embeddings | `backend/app/services/embedding_service.py` |
| Knowledge graph (GPT-4) | `backend/app/services/knowledge_extraction_service.py` |
| Retrieval (RAG) | `backend/app/services/rag_service.py` |
| Agentes / prompts / chat / review | `backend/app/services/agent_service.py` |
| Composición de pipeline | `backend/app/services/pipeline_composer.py` |
| Endpoints chat/review | `backend/app/api/endpoints/chat.py`, `agents.py` |
| Modelos | `backend/app/models/database.py` |
| Parámetros | `backend/app/config.py` |

> ⚠️ Nota operativa (deploy): `embedding_service.py` instancia `AsyncOpenAI(api_key=settings.OPENAI_API_KEY)`
> a nivel de módulo, así que **todo este pipeline requiere `OPENAI_API_KEY`** — incluso si `AI_PROVIDER=anthropic`
> (Anthropic genera el texto, pero los **embeddings** son siempre de OpenAI). Sin esa key el backend ni siquiera importa.
