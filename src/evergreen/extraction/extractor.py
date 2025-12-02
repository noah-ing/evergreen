"""
Entity extraction using GLiNER2.

Extracts named entities from text with support for:
- Standard NER types (Person, Organization, Location, etc.)
- Custom entity types via LLM fallback
- Relationship extraction between entities
"""

import asyncio
from typing import Any
from uuid import uuid4

import structlog

from evergreen.config import settings
from evergreen.models import DocumentChunk, Entity, EntityMention, Relationship

logger = structlog.get_logger()


# Default entity types for extraction
DEFAULT_ENTITY_TYPES = [
    "person",
    "organization", 
    "location",
    "product",
    "project",
    "technology",
    "date",
    "money",
    "email",
    "phone",
]

# Business-specific entity types
BUSINESS_ENTITY_TYPES = [
    "customer",
    "vendor",
    "contract",
    "meeting",
    "deadline",
    "department",
    "role",
]


class EntityExtractor:
    """
    GLiNER-based entity extraction.
    
    Uses the GLiNER2 model (205M params) for zero-shot NER.
    Falls back to LLM for complex entity types or relationship extraction.
    """

    def __init__(
        self,
        model_name: str = "urchade/gliner_multi_pii-v1",
        device: str = "auto",
        entity_types: list[str] | None = None,
        use_llm_fallback: bool = True,
    ):
        """
        Initialize entity extractor.
        
        Args:
            model_name: GLiNER model from HuggingFace
            device: Device to use (auto, cuda, cpu, mps)
            entity_types: Custom entity types to extract
            use_llm_fallback: Whether to use LLM for complex extraction
        """
        self.model_name = model_name
        self.entity_types = entity_types or DEFAULT_ENTITY_TYPES + BUSINESS_ENTITY_TYPES
        self.use_llm_fallback = use_llm_fallback
        
        self._model = None
        self._device = device
        
        logger.info(
            "Entity extractor initialized",
            model=model_name,
            entity_types=len(self.entity_types),
        )

    def _load_model(self):
        """Lazy load the GLiNER model."""
        if self._model is None:
            try:
                from gliner import GLiNER
                
                # Determine device
                device = self._device
                if device == "auto":
                    import torch
                    if torch.cuda.is_available():
                        device = "cuda"
                    elif torch.backends.mps.is_available():
                        device = "mps"
                    else:
                        device = "cpu"
                
                self._model = GLiNER.from_pretrained(self.model_name)
                self._model = self._model.to(device)
                
                logger.info("GLiNER model loaded", device=device)
                
            except ImportError:
                raise ImportError(
                    "gliner package required. Install with: pip install gliner"
                )
        
        return self._model

    async def extract(
        self,
        text: str,
        threshold: float = 0.5,
        flat_ner: bool = True,
    ) -> list[dict[str, Any]]:
        """
        Extract entities from text.
        
        Args:
            text: Text to extract entities from
            threshold: Confidence threshold (0-1)
            flat_ner: If True, don't allow nested entities
            
        Returns:
            List of extracted entities with positions
        """
        if not text or not text.strip():
            return []
        
        # Run model in thread pool (it's synchronous)
        loop = asyncio.get_event_loop()
        
        def _extract():
            model = self._load_model()
            return model.predict_entities(
                text,
                self.entity_types,
                threshold=threshold,
                flat_ner=flat_ner,
            )
        
        raw_entities = await loop.run_in_executor(None, _extract)
        
        # Convert to structured format
        entities = []
        for ent in raw_entities:
            entities.append({
                "text": ent["text"],
                "type": ent["label"].lower(),
                "start": ent["start"],
                "end": ent["end"],
                "confidence": ent["score"],
            })
        
        logger.debug(
            "Entities extracted",
            text_length=len(text),
            entity_count=len(entities),
        )
        
        return entities

    async def extract_from_chunk(
        self,
        chunk: DocumentChunk,
        threshold: float = 0.5,
    ) -> tuple[list[Entity], list[EntityMention]]:
        """
        Extract entities from a document chunk.
        
        Args:
            chunk: Document chunk to process
            threshold: Confidence threshold
            
        Returns:
            Tuple of (entities, mentions)
        """
        raw_entities = await self.extract(chunk.content, threshold=threshold)
        
        entities = []
        mentions = []
        entity_map = {}  # Deduplicate by (name, type)
        
        for raw in raw_entities:
            key = (raw["text"].lower(), raw["type"])
            
            if key not in entity_map:
                entity = Entity(
                    id=uuid4(),
                    tenant_id=chunk.tenant_id,
                    name=raw["text"],
                    type=raw["type"],
                    metadata={
                        "first_seen_document": chunk.document_id,
                        "confidence": raw["confidence"],
                    },
                )
                entity_map[key] = entity
                entities.append(entity)
            
            # Create mention
            mention = EntityMention(
                entity_id=entity_map[key].id,
                document_id=chunk.document_id,
                chunk_id=chunk.id,
                text=raw["text"],
                start_position=raw["start"],
                end_position=raw["end"],
                confidence=raw["confidence"],
            )
            mentions.append(mention)
        
        return entities, mentions

    async def extract_relationships(
        self,
        text: str,
        entities: list[Entity],
    ) -> list[Relationship]:
        """
        Extract relationships between entities.
        
        Uses LLM for relationship extraction as GLiNER
        doesn't support this natively.
        
        Args:
            text: Source text
            entities: Entities found in text
            
        Returns:
            List of relationships
        """
        if not self.use_llm_fallback or len(entities) < 2:
            return []
        
        # TODO: Implement LLM-based relationship extraction
        # For now, use simple co-occurrence heuristic
        relationships = []
        
        # Entities that appear in same text are related
        for i, source in enumerate(entities):
            for target in entities[i+1:]:
                # Create weak relationship based on co-occurrence
                rel = Relationship(
                    id=uuid4(),
                    source_entity_id=source.id,
                    target_entity_id=target.id,
                    relation_type="co_occurs_with",
                    confidence=0.3,  # Low confidence for co-occurrence
                    metadata={
                        "extraction_method": "co_occurrence",
                    },
                )
                relationships.append(rel)
        
        return relationships


class LLMEntityExtractor:
    """
    LLM-based entity extraction for complex cases.
    
    Used as fallback when GLiNER doesn't support certain entity types
    or for relationship extraction.
    """

    def __init__(self, model: str = "claude-3-5-sonnet-20241022"):
        """
        Initialize LLM extractor.
        
        Args:
            model: LLM model to use
        """
        self.model = model
        self._client = None

    def _get_client(self):
        """Lazy load Anthropic client."""
        if self._client is None:
            import anthropic
            self._client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
        return self._client

    async def extract_entities(
        self,
        text: str,
        entity_types: list[str],
    ) -> list[dict[str, Any]]:
        """
        Extract entities using LLM.
        
        Args:
            text: Text to extract from
            entity_types: Types of entities to look for
            
        Returns:
            List of extracted entities
        """
        client = self._get_client()
        
        prompt = f"""Extract the following types of entities from the text: {', '.join(entity_types)}

Text:
{text}

Return a JSON array of objects with keys: "text", "type", "confidence" (0-1).
Only return the JSON array, no other text."""

        response = await client.messages.create(
            model=self.model,
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
        )
        
        # Parse JSON response
        import json
        try:
            content = response.content[0].text
            # Clean up markdown code blocks if present
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]
            
            return json.loads(content.strip())
        except (json.JSONDecodeError, IndexError):
            logger.warning("Failed to parse LLM entity response")
            return []

    async def extract_relationships(
        self,
        text: str,
        entities: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """
        Extract relationships between entities using LLM.
        
        Args:
            text: Source text
            entities: List of entities found in text
            
        Returns:
            List of relationships
        """
        if len(entities) < 2:
            return []
        
        client = self._get_client()
        
        entity_list = "\n".join([f"- {e['text']} ({e['type']})" for e in entities])
        
        prompt = f"""Given these entities found in a text:
{entity_list}

And the original text:
{text}

Identify relationships between these entities. Return a JSON array of objects with:
- "source": source entity text
- "target": target entity text  
- "relation_type": type of relationship (e.g., "works_for", "manages", "located_in", "owns", "part_of")
- "confidence": confidence score 0-1

Only return the JSON array, no other text."""

        response = await client.messages.create(
            model=self.model,
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
        )
        
        import json
        try:
            content = response.content[0].text
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]
            
            return json.loads(content.strip())
        except (json.JSONDecodeError, IndexError):
            logger.warning("Failed to parse LLM relationship response")
            return []


async def extract_entities(
    text: str,
    entity_types: list[str] | None = None,
    use_llm: bool = False,
) -> list[dict[str, Any]]:
    """
    Convenience function for entity extraction.
    
    Args:
        text: Text to extract from
        entity_types: Custom entity types (uses defaults if None)
        use_llm: If True, use LLM instead of GLiNER
        
    Returns:
        List of extracted entities
    """
    if use_llm:
        extractor = LLMEntityExtractor()
        return await extractor.extract_entities(
            text,
            entity_types or DEFAULT_ENTITY_TYPES,
        )
    else:
        extractor = EntityExtractor(entity_types=entity_types)
        return await extractor.extract(text)
