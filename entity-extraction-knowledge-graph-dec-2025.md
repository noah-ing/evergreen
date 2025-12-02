# Entity Extraction for Business Knowledge Graphs - December 2025

## Executive Summary

**Recommended Approach**: **GLiNER** for local/privacy-focused extraction, **LLM + Instructor** for highest accuracy on complex business documents.

---

## Approach Comparison

### 1. spaCy NER (Transformer Models)

**Best for**: High-throughput production pipelines with standard entity types

| Aspect | Details |
|--------|---------|
| **Models** | `en_core_web_trf` (RoBERTa-based), custom fine-tuned |
| **Speed** | ~500-2000 docs/sec (CPU), ~10,000+ (GPU) |
| **Accuracy** | 90%+ on standard entities (PERSON, ORG, DATE) |
| **Setup** | `pip install spacy && python -m spacy download en_core_web_trf` |

```python
import spacy
nlp = spacy.load("en_core_web_trf")
doc = nlp("John Smith from Acme Corp discussed the Q4 project on Dec 1, 2025.")
entities = [(ent.text, ent.label_) for ent in doc.ents]
# [('John Smith', 'PERSON'), ('Acme Corp', 'ORG'), ('Dec 1, 2025', 'DATE')]
```

**Pros**: Battle-tested, excellent documentation, pipeline ecosystem  
**Cons**: Requires fine-tuning for custom entities (project names, topics)

---

### 2. GLiNER (Zero-Shot Entity Extraction) ⭐ RECOMMENDED FOR LOCAL

**Best for**: Custom entity types without training data, privacy-first deployments

| Aspect | Details |
|--------|---------|
| **Models** | `gliner_medium-v2.1` (general), `gliner_multi-v2.1` (multilingual) |
| **Speed** | ~100-500 docs/sec (CPU), ~2000+ (GPU) |
| **Accuracy** | 85-95% depending on entity clarity |
| **Size** | 205M params (GLiNER2 base) |

```python
from gliner import GLiNER

model = GLiNER.from_pretrained("urchade/gliner_medium-v2.1")

text = "Sarah Chen and Mike Johnson discussed the Atlas Project with Acme Corp last Tuesday."
labels = ["person", "company", "project name", "date"]

entities = model.predict_entities(text, labels, threshold=0.5)
# [{'text': 'Sarah Chen', 'label': 'person'}, 
#  {'text': 'Mike Johnson', 'label': 'person'},
#  {'text': 'Atlas Project', 'label': 'project name'},
#  {'text': 'Acme Corp', 'label': 'company'},
#  {'text': 'last Tuesday', 'label': 'date'}]
```

**GLiNER2** (Nov 2025): Adds text classification + structured extraction in one pass:
```python
from gliner2 import GLiNER2
extractor = GLiNER2.from_pretrained("fastino/gliner2-base-v1")

result = extractor.extract_json(text, {
    "meeting": [
        "attendees::list::Names of people",
        "company::str::Organization discussed",
        "project::str::Project name mentioned",
        "date::str::When the meeting occurred"
    ]
})
```

**Pros**: Zero-shot (no training), handles custom entities, fully local, CPU-efficient  
**Cons**: Lower accuracy than fine-tuned models on standard entities

---

### 3. LLM-Based Extraction (Structured Outputs) ⭐ RECOMMENDED FOR ACCURACY

**Best for**: Complex documents, nuanced extraction, highest accuracy

| Aspect | Details |
|--------|---------|
| **Libraries** | `instructor` (Pydantic validation), native structured outputs |
| **Speed** | ~1-10 docs/sec (API), ~0.5-2 docs/sec (local LLM) |
| **Accuracy** | 95%+ with good prompting |
| **Cost** | ~$0.001-0.01 per document (API) |

```python
import instructor
from pydantic import BaseModel
from typing import List, Optional

class BusinessEntity(BaseModel):
    people: List[str]
    organizations: List[str]
    projects: List[str]
    topics: List[str]
    dates: List[str]

# OpenAI/Anthropic API
client = instructor.from_provider("openai/gpt-4o-mini")

result = client.create(
    response_model=BusinessEntity,
    messages=[{
        "role": "user",
        "content": f"Extract entities from: {text}"
    }]
)

# Local with Ollama
client = instructor.from_provider("ollama/llama3.2")
```

**Pros**: Handles context, relationships, ambiguous cases; best for topics/themes  
**Cons**: Slower, API costs (unless local), potential rate limits

---

### 4. Dedicated NER Services

| Service | Strengths | Cost |
|---------|-----------|------|
| **AWS Comprehend** | PII detection, medical entities | $0.0001/unit |
| **Google Cloud NLP** | Sentiment + entities combined | $1/1000 units |
| **Azure Text Analytics** | Healthcare, PII focus | $1/1000 records |
| **Rosette** | 40+ languages, entity linking | Enterprise |

**Use when**: Compliance requirements, specific domains (medical/legal), enterprise scale

---

## Entity Type Recommendations

| Entity Type | Best Approach | Why |
|-------------|--------------|-----|
| **People names** | spaCy or GLiNER | Well-established patterns |
| **Companies/Orgs** | spaCy or GLiNER | Standard NER category |
| **Project names** | GLiNER or LLM | Custom entities, zero-shot needed |
| **Topics/themes** | LLM | Requires semantic understanding |
| **Dates/temporal** | spaCy + `dateparser` | Normalization important |

---

## Entity Resolution (Deduplication)

**Problem**: "John Smith", "J. Smith", "John", "Mr. Smith" → same person

### Approaches

#### 1. Coreference Resolution (spaCy Coreferee)
```python
import spacy
import coreferee

nlp = spacy.load('en_core_web_trf')
nlp.add_pipe('coreferee')

doc = nlp("John Smith joined Acme. He led the Atlas project. Smith presented results.")
doc._.coref_chains.print()
# 0: John Smith(0), He(4), Smith(9)
```

#### 2. String Similarity Clustering
```python
from rapidfuzz import fuzz, process

def cluster_entities(entities, threshold=85):
    clusters = []
    for entity in entities:
        matched = False
        for cluster in clusters:
            if fuzz.ratio(entity.lower(), cluster[0].lower()) >= threshold:
                cluster.append(entity)
                matched = True
                break
        if not matched:
            clusters.append([entity])
    return clusters

# cluster_entities(["John Smith", "J. Smith", "John", "Jane Doe"])
# [['John Smith', 'J. Smith', 'John'], ['Jane Doe']]
```

#### 3. Embedding-Based Clustering
```python
from sentence_transformers import SentenceTransformer
from sklearn.cluster import DBSCAN

model = SentenceTransformer('all-MiniLM-L6-v2')
embeddings = model.encode(entity_list)
clusters = DBSCAN(eps=0.3, min_samples=1, metric='cosine').fit(embeddings)
```

#### 4. LLM-Based Resolution
```python
class ResolvedEntities(BaseModel):
    canonical_name: str
    aliases: List[str]
    confidence: float

# Prompt LLM to group aliases to canonical forms
```

**Recommendation**: Use **coreference** for within-document, **embedding clustering** for cross-document resolution.

---

## Speed vs Accuracy Tradeoffs

| Approach | Speed (docs/sec) | Accuracy | Local? | Best Use Case |
|----------|-----------------|----------|--------|---------------|
| spaCy (sm) | 5000+ | 85% | ✅ | High-volume, standard entities |
| spaCy (trf) | 500-2000 | 91% | ✅ | Production NER |
| GLiNER | 100-500 | 87% | ✅ | Custom entities, no training |
| GLiNER2 | 50-200 | 89% | ✅ | Multi-task extraction |
| LLM (local) | 0.5-2 | 92% | ✅ | Complex docs, limited volume |
| LLM (API) | 1-10 | 95% | ❌ | Highest accuracy needed |

---

## Recommended Architecture for Business Documents

```
┌─────────────────────────────────────────────────────────────┐
│                    Document Pipeline                         │
├─────────────────────────────────────────────────────────────┤
│  1. Pre-processing                                          │
│     └── Text extraction, chunking, language detection       │
├─────────────────────────────────────────────────────────────┤
│  2. Fast Pass (GLiNER)                                      │
│     └── Extract: people, orgs, dates, locations             │
│     └── Flag low-confidence entities for LLM review         │
├─────────────────────────────────────────────────────────────┤
│  3. LLM Pass (selective)                                    │
│     └── Extract: projects, topics, themes                   │
│     └── Resolve ambiguous entities from fast pass           │
├─────────────────────────────────────────────────────────────┤
│  4. Entity Resolution                                       │
│     └── Coreferee for within-document                       │
│     └── Embedding clustering for cross-document             │
├─────────────────────────────────────────────────────────────┤
│  5. Knowledge Graph Population                              │
│     └── Store canonical entities + relationships            │
└─────────────────────────────────────────────────────────────┘
```

---

## Fully Local Setup (No API Calls)

```bash
# Install stack
pip install gliner gliner2 spacy instructor ollama
pip install coreferee rapidfuzz sentence-transformers
python -m spacy download en_core_web_trf
python -m coreferee install en

# Pull local LLM
ollama pull llama3.2
```

```python
# Complete local pipeline
from gliner2 import GLiNER2
import instructor
import spacy

# Fast extraction
gliner = GLiNER2.from_pretrained("fastino/gliner2-base-v1")

# Coreference
nlp = spacy.load("en_core_web_trf")
nlp.add_pipe("coreferee")

# Complex extraction (local LLM)
llm_client = instructor.from_provider("ollama/llama3.2")

def extract_entities(text):
    # GLiNER for standard entities
    entities = gliner.extract_entities(
        text, 
        ["person", "company", "project", "date", "location"]
    )
    
    # Coreferee for resolution
    doc = nlp(text)
    coref_chains = doc._.coref_chains
    
    # LLM for topics (if needed)
    topics = llm_client.create(
        response_model=TopicExtraction,
        messages=[{"role": "user", "content": f"Extract topics: {text}"}]
    )
    
    return {**entities, "topics": topics, "coreferences": coref_chains}
```

---

## Key Recommendations

1. **Start with GLiNER** for custom business entities - zero training, good accuracy
2. **Add spaCy** for high-volume standard NER (people, orgs, dates)
3. **Use LLM selectively** for topics, themes, and ambiguous cases
4. **Entity resolution is critical** - plan for it from day one
5. **Test on your actual documents** - business jargon varies significantly

### For Emails Specifically
- GLiNER handles informal mentions well
- Consider email-specific patterns (signatures, quoted text)
- Temporal expressions need normalization (e.g., "next Tuesday")

### For Documents (Word, PDF)
- Extract structure metadata (headers, sections)
- Use section context for entity disambiguation
- Consider document type (contract vs. memo vs. report)
