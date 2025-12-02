# Enterprise Knowledge Retrieval System: State-of-the-Art Research (December 2025)

## Executive Summary

This comprehensive research document provides actionable recommendations for building a "Second Brain" product for SMBs that indexes M365/Google Workspace data. The findings are based on the current landscape of embedding models, vector databases, chunking strategies, and retrieval techniques.

---

## 1. Embedding Models Comparison

### Overview Matrix

| Model | Dimensions | Context Window | Multilingual | Code/Tech | Cost per 1M Tokens | Best For |
|-------|------------|----------------|--------------|-----------|-------------------|----------|
| **OpenAI text-embedding-3-large** | 3072 (adjustable to 256-3072) | 8,191 | Good (MIRACL 54.9%) | Good | $0.13 | General enterprise, balanced cost/quality |
| **OpenAI text-embedding-3-small** | 1536 (adjustable) | 8,191 | Moderate (MIRACL 44%) | Good | $0.02 | Cost-sensitive applications |
| **Cohere embed-v4.0** | 256-1536 | 128K | 100+ languages | Good | ~$0.10 | Multimodal (text+images), long docs |
| **Cohere embed-multilingual-v3.0** | 1024 | 512 | 100+ languages | Moderate | ~$0.10 | Multilingual-heavy workloads |
| **BGE-M3** | 1024 | 8,192 | 100+ languages | Good | Free (self-hosted) | Hybrid retrieval, budget-conscious |
| **Jina embeddings v3** | 1024 | 8,192 | 89+ languages | Excellent | ~$0.02 | Technical docs, code |
| **Voyage AI voyage-3-large** | 256-2048 | 32,000 | Excellent | Excellent | ~$0.06 | Enterprise documents, long context |
| **Voyage AI voyage-code-3** | 256-2048 | 32,000 | N/A | Best-in-class | ~$0.06 | Code repositories |
| **Voyage AI voyage-finance-2** | 1024 | 32,000 | N/A | N/A | ~$0.06 | Financial documents |

### Detailed Analysis

#### OpenAI text-embedding-3-large
- **Strengths**: 
  - Matryoshka representation learning (can shorten embeddings without losing concept-representing properties)
  - Strong MTEB benchmark performance (64.6%)
  - Seamless API integration
  - Excellent general-purpose performance
- **Weaknesses**: 
  - Higher cost than alternatives
  - 8K context window limits long document handling
  - Closed source (vendor lock-in risk)
- **Best Use Case**: Enterprise teams already using OpenAI stack

#### Cohere embed-v4.0 (Latest)
- **Strengths**:
  - **128K context window** - longest commercial context available
  - Multimodal support (text + images)
  - 100+ language support with excellent quality
  - Good compression support (binary quantization)
- **Weaknesses**:
  - Newer model, less battle-tested
  - Higher cost for long documents
- **Best Use Case**: Multilingual enterprises, PDF/document-heavy workloads

#### BGE-M3 (Open Source Leader)
- **Strengths**:
  - **Multi-functionality**: Dense, sparse, AND multi-vector (ColBERT) in one model
  - **Free**: MIT licensed, self-hostable
  - 8,192 token context window
  - Outperforms OpenAI on multilingual benchmarks
  - Native hybrid retrieval support (dense + sparse)
- **Weaknesses**:
  - Requires self-hosting (GPU infrastructure)
  - Higher operational complexity
  - ~567M parameters (requires decent GPU)
- **Best Use Case**: Cost-conscious startups, hybrid search requirements

#### Voyage AI (Emerging Leader)
- **Strengths**:
  - **32,000 token context** - longest for enterprise models
  - Domain-specific models (finance, legal, code)
  - Best-in-class code retrieval with voyage-code-3
  - Flexible output dimensions (256-2048)
  - Binary quantization support
- **Weaknesses**:
  - Newer entrant (less ecosystem integration)
  - Limited compared to OpenAI in some benchmarks
- **Best Use Case**: Long document enterprises, code-heavy knowledge bases

### 🏆 Recommendation for "Second Brain" Product

**Primary Choice: Voyage AI voyage-3.5** or **voyage-3-large**
- 32K context handles long emails, documents, meeting transcripts
- Flexible dimensions (start with 1024, compress to 256 for cost savings)
- Strong multilingual support for global teams
- Competitive pricing

**Budget Alternative: BGE-M3 (self-hosted)**
- Hybrid retrieval out-of-the-box
- Zero API costs
- Excellent for M365/Google Workspace document types

**Fallback/Easy Integration: OpenAI text-embedding-3-large**
- Simplest integration
- Well-documented
- Use dimension reduction (1024 dims) to balance cost/performance

---

## 2. Vector Databases Comparison

### Overview Matrix

| Database | Type | Scalability (SMB) | Hybrid Search | Filtering | Managed Cost | Self-Hosted |
|----------|------|-------------------|---------------|-----------|--------------|-------------|
| **Pinecone** | Fully Managed | Excellent | Yes | Good | $70+/mo | No |
| **Weaviate** | Both | Excellent | Native | Excellent | $45-280/mo | Yes (K8s) |
| **Qdrant** | Both | Excellent | Native | Excellent | $0+/mo | Yes (Docker) |
| **Milvus** | Both | Enterprise-grade | Native | Excellent | Zilliz Cloud | Yes (Docker/K8s) |
| **ChromaDB** | Self-hosted | Good (<1M) | Limited | Good | N/A | Yes (Docker) |
| **pgvector** | Postgres Extension | Good (<10M) | Native (w/FTS) | Excellent | DB cost | Yes (any PG) |

### Detailed Analysis

#### Pinecone
- **Strengths**:
  - Zero operational overhead
  - Excellent developer experience
  - Built-in reranking via Inference API
  - Serverless pricing (pay for what you use)
  - 1GB free forever tier
- **Weaknesses**:
  - Vendor lock-in
  - Cost scales with usage
  - Limited self-hosting options
- **Pricing**: 
  - Starter: Free (2GB storage, limited reads/writes)
  - Standard: $70/mo minimum + usage
- **Best For**: Teams wanting zero-ops managed solution

#### Weaviate
- **Strengths**:
  - Native hybrid search (BM25 + vector)
  - Multi-tenancy support
  - Built-in embedding service
  - Query Agent for natural language queries
  - Strong compression (PQ, BQ, SQ)
  - HIPAA compliant (Enterprise)
- **Weaknesses**:
  - Complex K8s deployment for self-hosted
  - Learning curve for advanced features
- **Pricing**:
  - Free Trial: 14 days
  - Flex: From $45/mo (shared cloud)
  - Plus: From $280/mo (dedicated options)
- **Best For**: Enterprises needing hybrid search + multi-tenancy

#### Qdrant
- **Strengths**:
  - **1GB free forever** cluster
  - Written in Rust (excellent performance)
  - Native hybrid search
  - Easy Docker deployment
  - Payload (metadata) filtering is excellent
  - Quantization support
- **Weaknesses**:
  - Smaller ecosystem than Pinecone/Weaviate
  - Less advanced managed features
- **Pricing**:
  - Free: 1GB cluster forever
  - Managed Cloud: $0.014/hour starting
  - Hybrid Cloud: Bring your own infra
- **Best For**: Startups wanting balance of managed + control

#### Milvus
- **Strengths**:
  - Built for massive scale (billions of vectors)
  - Multiple index types (IVF, HNSW, GPU indexes)
  - Milvus Lite for development (pip install)
  - Strong hybrid search with BGE-M3 integration
  - Open source (Apache 2.0)
- **Weaknesses**:
  - Operational complexity at scale
  - Resource-intensive
- **Pricing**:
  - Milvus Lite/Standalone: Free
  - Zilliz Cloud: Pay-as-you-go
- **Best For**: Teams planning for massive scale or already on Zilliz

#### ChromaDB
- **Strengths**:
  - Simplest setup (pip install chromadb)
  - Great for prototyping
  - Python-native
  - In-memory option for speed
- **Weaknesses**:
  - Limited production features
  - Hybrid search is basic
  - Scalability limits
- **Best For**: Prototyping, small datasets (<500K vectors)

#### pgvector (PostgreSQL Extension)
- **Strengths**:
  - **Use existing Postgres infrastructure**
  - ACID compliance
  - Full SQL capabilities
  - Native hybrid search with Postgres full-text search
  - Excellent filtering with standard SQL WHERE clauses
  - HNSW and IVFFlat indexes
  - Supabase integration for managed option
- **Weaknesses**:
  - Performance at scale (>10M vectors)
  - Index dimension limits (2000 for HNSW, 4000 for halfvec)
  - Requires Postgres expertise
- **Best For**: Teams with existing Postgres, simpler deployments

### 🏆 Recommendation for "Second Brain" Product

**For SMB Startup Building Retrieval Product:**

**Primary Choice: Qdrant**
- Free 1GB cluster to start
- Excellent hybrid search for M365/Google Workspace mix of content
- Easy Docker self-hosting when you scale
- Strong payload filtering for metadata (sender, date, folder, etc.)
- Rust performance for production workloads

**Alternative for Postgres Shops: pgvector + Supabase**
- Zero new infrastructure if you're on Postgres
- Native SQL filtering is perfect for complex queries
- Hybrid search via Postgres FTS + pgvector
- Supabase managed option available

**For Zero-Ops Teams: Pinecone**
- Get to market fastest
- Built-in inference (embeddings + reranking)
- Focus on product, not infrastructure

---

## 3. Chunking Strategies for Enterprise Documents

### Document Type Strategies

#### Emails
```
Strategy: Conversation-aware chunking
- Chunk Size: 512-1024 tokens
- Method: Preserve email thread structure
- Include: Subject, sender, date as metadata
- Handle Forwards/Replies: Extract unique content, reference thread
```

**Implementation:**
```python
def chunk_email_thread(thread):
    chunks = []
    for email in thread.messages:
        # Extract clean body (remove quoted replies)
        clean_body = remove_quoted_text(email.body)
        
        # Create metadata-rich chunk
        chunk = {
            "text": f"Subject: {email.subject}\nFrom: {email.sender}\nDate: {email.date}\n\n{clean_body}",
            "metadata": {
                "thread_id": thread.id,
                "message_id": email.id,
                "sender": email.sender,
                "date": email.date,
                "recipients": email.recipients,
                "attachments": [a.name for a in email.attachments]
            }
        }
        chunks.append(chunk)
    return chunks
```

#### Slack Messages
```
Strategy: Thread-based chunking with context
- Chunk Size: 256-512 tokens per thread
- Method: Group by thread/channel context
- Include: Channel, thread participants, timestamp range
- Context Window: Include 2-3 messages before for context
```

**Implementation:**
```python
def chunk_slack_thread(thread, channel_name):
    # Combine thread into single chunk if under limit
    full_thread = "\n".join([
        f"[{m.timestamp}] {m.user}: {m.text}" 
        for m in thread.messages
    ])
    
    if count_tokens(full_thread) <= 512:
        return [{
            "text": f"Channel: #{channel_name}\n\n{full_thread}",
            "metadata": {
                "channel": channel_name,
                "thread_ts": thread.ts,
                "participants": list(set(m.user for m in thread.messages)),
                "date_range": f"{thread.messages[0].date} - {thread.messages[-1].date}"
            }
        }]
    else:
        # Split with overlap for longer threads
        return split_with_overlap(full_thread, chunk_size=512, overlap=100)
```

#### Documents (Word, PDF, Google Docs)
```
Strategy: Semantic/Structural chunking
- Chunk Size: 512-1024 tokens (test for your domain)
- Method: Respect document structure (headers, sections)
- Include: Document title, section headers, page numbers
- Long Documents: Use hierarchical chunking
```

**Best Practices:**
1. **Structural Chunking First**: Split on headers (H1, H2, H3)
2. **Semantic Chunking Second**: Use embedding similarity to find topic boundaries
3. **Contextual Enrichment**: Prepend section path (Document > Chapter > Section)

```python
def chunk_document(doc):
    chunks = []
    
    for section in doc.sections:
        section_text = section.content
        section_path = f"{doc.title} > {section.header}"
        
        if count_tokens(section_text) <= 1024:
            chunks.append({
                "text": f"{section_path}\n\n{section_text}",
                "metadata": {
                    "doc_id": doc.id,
                    "section": section.header,
                    "page_range": section.pages
                }
            })
        else:
            # Use semantic chunking for long sections
            sub_chunks = semantic_chunk(section_text, max_tokens=512)
            for i, sub in enumerate(sub_chunks):
                chunks.append({
                    "text": f"{section_path} (Part {i+1})\n\n{sub}",
                    "metadata": {...}
                })
    
    return chunks
```

#### Meeting Notes/Transcripts
```
Strategy: Topic-based chunking with speaker attribution
- Chunk Size: 1024-2048 tokens (longer for context)
- Method: Segment by topic shifts or time blocks
- Include: Meeting title, date, attendees, action items
- Special: Extract action items as separate indexed chunks
```

### Chunking Method Comparison

| Method | Best For | Pros | Cons |
|--------|----------|------|------|
| **Fixed-size** | Homogeneous content | Simple, predictable | May split mid-sentence |
| **Recursive Character** | General documents | Respects paragraphs | No semantic awareness |
| **Sentence-based** | Short-form content | Clean boundaries | May lose context |
| **Semantic** | Mixed content | Respects topics | Slower, requires embeddings |
| **Document-aware** | Structured docs | Preserves structure | Document-type specific |
| **Contextual (Anthropic)** | Complex docs | Best retrieval | Expensive (LLM calls) |

### 🏆 Recommendation for M365/Google Workspace

**Hybrid Approach:**
1. **Document-aware first**: Use structure (headers, threads) as primary splitter
2. **Semantic validation**: Check chunk coherence with embedding similarity
3. **Contextual enrichment**: Add document/section context to chunks

**Optimal Settings by Type:**
- Emails: 512 tokens, thread-aware
- Slack: 256-512 tokens, thread-grouped
- Documents: 512-1024 tokens, section-aware
- Meeting notes: 1024 tokens, topic-segmented

**Key Principle**: Chunks should make sense standalone. If a human can't understand the chunk without context, neither can the retrieval system.

---

## 4. Retrieval Strategies (RAG Best Practices 2025)

### The Modern RAG Stack

```
User Query
    ↓
[Query Processing] ← Query expansion, rewriting
    ↓
[Hybrid Retrieval] ← Dense + Sparse search
    ↓
[Reranking] ← Cross-encoder scoring
    ↓
[Context Assembly] ← Chunk expansion, deduplication
    ↓
[LLM Generation] ← Grounded response
```

### Hybrid Search (Dense + Sparse)

**Why Hybrid Search:**
- Dense (vector): Captures semantic meaning
- Sparse (BM25/keyword): Captures exact terms, names, IDs
- Combined: Best of both worlds

**Implementation Options:**

1. **BGE-M3 Native** (Recommended for self-hosted):
```python
from FlagEmbedding import BGEM3FlagModel

model = BGEM3FlagModel('BAAI/bge-m3', use_fp16=True)

# Get both dense and sparse embeddings in one call
output = model.encode(
    texts, 
    return_dense=True, 
    return_sparse=True
)

dense_embeddings = output['dense_vecs']
sparse_embeddings = output['lexical_weights']
```

2. **Qdrant Hybrid Search**:
```python
from qdrant_client import QdrantClient

client = QdrantClient("localhost", port=6333)

# Hybrid search with RRF fusion
results = client.query_points(
    collection_name="documents",
    prefetch=[
        # Dense search
        models.Prefetch(
            query=dense_vector,
            using="dense",
            limit=20
        ),
        # Sparse search  
        models.Prefetch(
            query=sparse_vector,
            using="sparse",
            limit=20
        )
    ],
    query=models.FusionQuery(fusion=models.Fusion.RRF)
)
```

3. **pgvector + Postgres FTS**:
```sql
-- Hybrid search with Reciprocal Rank Fusion
WITH semantic_search AS (
    SELECT id, RANK() OVER (ORDER BY embedding <=> query_embedding) as rank
    FROM documents
    ORDER BY embedding <=> query_embedding
    LIMIT 20
),
keyword_search AS (
    SELECT id, RANK() OVER (ORDER BY ts_rank_cd(textsearch, query) DESC) as rank
    FROM documents, plainto_tsquery('search terms') query
    WHERE textsearch @@ query
    ORDER BY ts_rank_cd(textsearch, query) DESC
    LIMIT 20
)
SELECT 
    COALESCE(s.id, k.id) as id,
    COALESCE(1.0 / (60 + s.rank), 0.0) + 
    COALESCE(1.0 / (60 + k.rank), 0.0) as score
FROM semantic_search s
FULL OUTER JOIN keyword_search k ON s.id = k.id
ORDER BY score DESC
LIMIT 10;
```

### Reranking

**Why Rerank:**
- Bi-encoders (embedding models) are fast but less accurate
- Cross-encoders compare query-document pairs directly
- 10-30% improvement in retrieval quality typical

**Options:**

| Reranker | Quality | Speed | Cost |
|----------|---------|-------|------|
| **Cohere rerank-v3.5** | Excellent | Fast | ~$1/1000 searches |
| **Voyage rerank-2.5** | Excellent | Fast | ~$0.05/1M tokens |
| **BGE-reranker-v2-m3** | Good | Fast | Free (self-hosted) |
| **Cross-encoder MS MARCO** | Good | Slow | Free (self-hosted) |

**Implementation (Cohere):**
```python
import cohere

co = cohere.ClientV2()

# First: Get top-20 from hybrid search
initial_results = hybrid_search(query, limit=20)

# Then: Rerank to get top-5
reranked = co.rerank(
    model="rerank-v3.5",
    query=query,
    documents=[r.text for r in initial_results],
    top_n=5
)

final_results = [initial_results[r.index] for r in reranked.results]
```

### Advanced RAG Techniques

#### 1. Query Expansion/Rewriting
Generate multiple query variants to improve recall:

```python
def expand_query(original_query):
    prompt = f"""Given the query: "{original_query}"
    Generate 3 alternative phrasings that might match relevant documents.
    Return as a JSON array."""
    
    expanded = llm.generate(prompt)
    return [original_query] + json.loads(expanded)
```

#### 2. Contextual Retrieval (Anthropic Method)
Prepend context to chunks before embedding:

```python
def add_context_to_chunk(chunk, full_document):
    prompt = f"""<document>
{full_document}
</document>

Here is the chunk:
<chunk>
{chunk}
</chunk>

Please give a short succinct context to situate this chunk within 
the overall document for the purposes of improving search retrieval. 
Answer only with the succinct context and nothing else."""
    
    context = llm.generate(prompt)
    return f"{context}\n\n{chunk}"
```

#### 3. Multi-Step/Agentic RAG
For complex queries, use iterative retrieval:

```python
def agentic_rag(query):
    # Step 1: Initial retrieval
    initial_context = retrieve(query)
    
    # Step 2: Evaluate if more info needed
    evaluation = llm.generate(f"""
    Query: {query}
    Retrieved context: {initial_context}
    
    Is this context sufficient to answer the query? 
    If not, what additional information is needed?
    """)
    
    if needs_more_info(evaluation):
        # Step 3: Generate follow-up query
        follow_up = extract_follow_up_query(evaluation)
        additional_context = retrieve(follow_up)
        final_context = deduplicate(initial_context + additional_context)
    else:
        final_context = initial_context
    
    # Step 4: Generate answer
    return llm.generate(f"""
    Query: {query}
    Context: {final_context}
    
    Answer the query based on the context provided.
    """)
```

#### 4. CRAG (Corrective RAG)
Evaluate retrieval quality and fall back to web search:

```python
def corrective_rag(query):
    retrieved = retrieve(query)
    
    # Evaluate retrieval quality
    scores = evaluate_relevance(query, retrieved)
    
    if max(scores) < 0.5:  # Low confidence
        # Fall back to web search
        web_results = web_search(query)
        retrieved = rerank(query, retrieved + web_results)
    
    return generate_answer(query, retrieved)
```

### 🏆 Recommended RAG Pipeline for "Second Brain"

```
1. Query Processing
   - Spell correction
   - Query expansion (generate 2-3 variants)
   
2. Hybrid Retrieval (Qdrant or pgvector)
   - Dense search: Voyage/OpenAI embeddings
   - Sparse search: BM25 or learned sparse (BGE-M3)
   - Fusion: Reciprocal Rank Fusion
   - Retrieve: Top 20 candidates
   
3. Metadata Filtering (at retrieval time)
   - Date ranges
   - Source types (email, doc, slack)
   - User/team permissions
   
4. Reranking
   - Cohere rerank-v3.5 or Voyage rerank-2.5
   - Rerank to top 5-10 results
   
5. Context Assembly
   - Chunk expansion (retrieve surrounding chunks)
   - Deduplication
   - Format for LLM context
   
6. Generation
   - GPT-4 / Claude for final response
   - Include citations/sources
```

---

## 5. Final Recommendations for "Second Brain" SMB Product

### Technology Stack

| Component | Primary Choice | Alternative |
|-----------|---------------|-------------|
| **Embedding Model** | Voyage AI voyage-3.5 | OpenAI text-embedding-3-large |
| **Vector Database** | Qdrant | pgvector (if Postgres-centric) |
| **Reranker** | Cohere rerank-v3.5 | Voyage rerank-2.5 |
| **Chunking** | LangChain RecursiveCharacterTextSplitter + custom | LlamaIndex NodeParser |
| **LLM for RAG** | Claude 3.5 Sonnet / GPT-4o | GPT-4o-mini for cost |

### Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│                    M365 / Google Workspace               │
│         (Emails, Docs, Slack, Calendar, Drive)          │
└────────────────────────┬────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────┐
│                  Ingestion Pipeline                      │
│  1. Extract (Microsoft Graph / Google APIs)             │
│  2. Parse (PDFs, HTML, DOCX)                            │
│  3. Chunk (Document-aware + Semantic)                   │
│  4. Enrich (Metadata extraction)                        │
│  5. Embed (Voyage AI voyage-3.5)                        │
└────────────────────────┬────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────┐
│                   Qdrant Vector DB                       │
│  - Collections per tenant                               │
│  - Dense + Sparse vectors                               │
│  - Metadata for filtering                               │
└────────────────────────┬────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────┐
│                  Retrieval Pipeline                      │
│  1. Query Processing (expansion, rewrite)               │
│  2. Hybrid Search (dense + sparse)                      │
│  3. Metadata Filtering (permissions, dates)             │
│  4. Reranking (Cohere rerank-v3.5)                      │
│  5. Context Assembly                                    │
└────────────────────────┬────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────┐
│                   LLM Generation                         │
│  - Claude 3.5 / GPT-4o                                  │
│  - Grounded responses with citations                    │
│  - Source attribution                                   │
└─────────────────────────────────────────────────────────┘
```

### Cost Estimation (100K-1M documents, 10 active users)

| Component | Monthly Cost Estimate |
|-----------|----------------------|
| Voyage AI Embeddings (initial + incremental) | $50-150 |
| Qdrant Cloud (managed) | $50-100 |
| Cohere Reranking | $30-100 |
| LLM (GPT-4o / Claude) | $100-500 |
| **Total** | **$230-850/mo** |

### Key Implementation Notes

1. **Start Simple**: Fixed-size chunking (512 tokens) → Evaluate → Add complexity
2. **Metadata is Critical**: Store source, date, author, permissions with every chunk
3. **Test Retrieval Quality**: Build evaluation dataset before optimizing
4. **Multi-tenancy**: Use collection-per-tenant or payload filtering in Qdrant
5. **Permissions**: Filter at retrieval time based on user's access rights
6. **Incremental Updates**: Build efficient sync with M365/Google change notifications

### Quick Start Code Example

```python
import voyageai
from qdrant_client import QdrantClient
import cohere

# Initialize clients
voyage = voyageai.Client()
qdrant = QdrantClient("localhost", port=6333)
cohere_client = cohere.ClientV2()

def ingest_document(doc_id, text, metadata):
    # 1. Chunk
    chunks = chunk_document(text, max_tokens=512)
    
    # 2. Embed
    embeddings = voyage.embed(
        [c["text"] for c in chunks],
        model="voyage-3.5",
        input_type="document"
    )
    
    # 3. Store in Qdrant
    qdrant.upsert(
        collection_name="knowledge_base",
        points=[
            {
                "id": f"{doc_id}_{i}",
                "vector": emb,
                "payload": {**chunk["metadata"], **metadata}
            }
            for i, (chunk, emb) in enumerate(zip(chunks, embeddings.embeddings))
        ]
    )

def search(query, filters=None):
    # 1. Embed query
    query_embedding = voyage.embed(
        [query], 
        model="voyage-3.5",
        input_type="query"
    ).embeddings[0]
    
    # 2. Hybrid search in Qdrant
    results = qdrant.search(
        collection_name="knowledge_base",
        query_vector=query_embedding,
        query_filter=filters,
        limit=20
    )
    
    # 3. Rerank
    reranked = cohere_client.rerank(
        model="rerank-v3.5",
        query=query,
        documents=[r.payload["text"] for r in results],
        top_n=5
    )
    
    return [results[r.index] for r in reranked.results]
```

---

## Appendix: Resources

### Documentation
- [Voyage AI Docs](https://docs.voyageai.com/)
- [Qdrant Documentation](https://qdrant.tech/documentation/)
- [BGE-M3 on HuggingFace](https://huggingface.co/BAAI/bge-m3)
- [Cohere Rerank](https://docs.cohere.com/docs/rerank)
- [pgvector GitHub](https://github.com/pgvector/pgvector)

### Benchmarks
- [MTEB Leaderboard](https://huggingface.co/spaces/mteb/leaderboard)
- [MIRACL (Multilingual)](https://github.com/project-miracl/miracl)

### Tutorials
- [Pinecone Chunking Guide](https://www.pinecone.io/learn/chunking-strategies/)
- [Anthropic Contextual Retrieval](https://www.anthropic.com/news/contextual-retrieval)
- [LlamaIndex RAG Evaluation](https://www.llamaindex.ai/blog/evaluating-the-ideal-chunk-size-for-a-rag-system-using-llamaindex-6207e5d3fec5)

---

*Research compiled: December 2025*
*For: Enterprise Knowledge Retrieval System / Second Brain Product*
