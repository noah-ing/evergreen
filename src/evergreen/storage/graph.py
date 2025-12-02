"""
Graph storage using FalkorDB.

Handles entity and relationship storage for knowledge graph queries.
"""

from typing import Any

import structlog
from falkordb import FalkorDB as FalkorDBClient
from redis.asyncio import Redis

from evergreen.config import settings
from evergreen.models import Entity, Relationship

logger = structlog.get_logger()


class GraphStore:
    """
    FalkorDB-based graph storage for entities and relationships.
    
    Features:
    - Tenant isolation via graph prefixing
    - Cypher query interface
    - Entity deduplication and merging
    - Subgraph extraction for context
    """

    def __init__(
        self,
        host: str | None = None,
        port: int | None = None,
    ):
        """
        Initialize graph store connection.
        
        Args:
            host: FalkorDB host (defaults to settings)
            port: FalkorDB port (defaults to settings)
        """
        self.host = host or settings.falkordb_host
        self.port = port or settings.falkordb_port
        
        # FalkorDB uses Redis protocol
        self._client = FalkorDBClient(
            host=self.host,
            port=self.port,
        )
        
        logger.info(
            "Graph store initialized",
            host=self.host,
            port=self.port,
        )

    def _graph_name(self, tenant_id: str) -> str:
        """Get graph name for a tenant."""
        return f"evergreen_{tenant_id}"

    def _get_graph(self, tenant_id: str):
        """Get graph instance for tenant."""
        return self._client.select_graph(self._graph_name(tenant_id))

    async def ensure_schema(self, tenant_id: str) -> None:
        """
        Ensure graph schema exists for tenant.
        
        Creates indices for efficient queries.
        
        Args:
            tenant_id: Tenant identifier
        """
        graph = self._get_graph(tenant_id)
        
        # Create indices for entity lookups
        try:
            graph.query("CREATE INDEX FOR (e:Entity) ON (e.id)")
            graph.query("CREATE INDEX FOR (e:Entity) ON (e.name)")
            graph.query("CREATE INDEX FOR (e:Entity) ON (e.type)")
            graph.query("CREATE INDEX FOR (d:Document) ON (d.id)")
            logger.info("Graph schema created", tenant_id=tenant_id)
        except Exception as e:
            # Indices may already exist
            logger.debug("Schema creation note", error=str(e))

    async def create_entity(
        self,
        tenant_id: str,
        entity: Entity,
    ) -> str:
        """
        Create or merge an entity node.
        
        Uses MERGE to handle deduplication.
        
        Args:
            tenant_id: Tenant identifier
            entity: Entity to create
            
        Returns:
            Entity ID
        """
        graph = self._get_graph(tenant_id)
        
        # Build properties
        props = {
            "id": str(entity.id),
            "name": entity.name,
            "type": entity.type,
            "tenant_id": entity.tenant_id,
        }
        
        # Add metadata as properties
        for key, value in entity.metadata.items():
            if isinstance(value, (str, int, float, bool)):
                props[key] = value
        
        # MERGE on name + type for deduplication
        query = """
        MERGE (e:Entity {name: $name, type: $type})
        ON CREATE SET e += $props
        ON MATCH SET e.mention_count = COALESCE(e.mention_count, 0) + 1
        RETURN e.id as id
        """
        
        result = graph.query(
            query,
            params={
                "name": entity.name,
                "type": entity.type,
                "props": props,
            },
        )
        
        logger.debug(
            "Entity created/merged",
            entity_name=entity.name,
            entity_type=entity.type,
        )
        
        return str(entity.id)

    async def create_relationship(
        self,
        tenant_id: str,
        relationship: Relationship,
    ) -> str:
        """
        Create a relationship between entities.
        
        Args:
            tenant_id: Tenant identifier
            relationship: Relationship to create
            
        Returns:
            Relationship ID
        """
        graph = self._get_graph(tenant_id)
        
        # Build relationship properties
        props = {
            "id": str(relationship.id),
            "type": relationship.relation_type,
            "confidence": relationship.confidence,
        }
        
        for key, value in relationship.metadata.items():
            if isinstance(value, (str, int, float, bool)):
                props[key] = value
        
        # Create relationship between entities
        query = """
        MATCH (source:Entity {id: $source_id})
        MATCH (target:Entity {id: $target_id})
        CREATE (source)-[r:RELATES_TO $props]->(target)
        RETURN r.id as id
        """
        
        result = graph.query(
            query,
            params={
                "source_id": str(relationship.source_entity_id),
                "target_id": str(relationship.target_entity_id),
                "props": props,
            },
        )
        
        logger.debug(
            "Relationship created",
            source_id=str(relationship.source_entity_id),
            target_id=str(relationship.target_entity_id),
            relation_type=relationship.relation_type,
        )
        
        return str(relationship.id)

    async def link_entity_to_document(
        self,
        tenant_id: str,
        entity_id: str,
        document_id: str,
        mention_text: str | None = None,
        position: int | None = None,
    ) -> None:
        """
        Create a link between an entity and its source document.
        
        Args:
            tenant_id: Tenant identifier
            entity_id: Entity ID
            document_id: Document ID
            mention_text: Text where entity was mentioned
            position: Character position in document
        """
        graph = self._get_graph(tenant_id)
        
        # Ensure document node exists
        doc_query = """
        MERGE (d:Document {id: $doc_id})
        RETURN d.id
        """
        graph.query(doc_query, params={"doc_id": document_id})
        
        # Create mention relationship
        props = {}
        if mention_text:
            props["mention_text"] = mention_text
        if position is not None:
            props["position"] = position
        
        link_query = """
        MATCH (e:Entity {id: $entity_id})
        MATCH (d:Document {id: $doc_id})
        CREATE (e)-[r:MENTIONED_IN $props]->(d)
        """
        
        graph.query(
            link_query,
            params={
                "entity_id": entity_id,
                "doc_id": document_id,
                "props": props,
            },
        )

    async def get_entity_subgraph(
        self,
        tenant_id: str,
        entity_id: str,
        depth: int = 2,
    ) -> dict[str, Any]:
        """
        Get subgraph around an entity.
        
        Args:
            tenant_id: Tenant identifier
            entity_id: Central entity ID
            depth: How many hops to traverse
            
        Returns:
            Subgraph with nodes and edges
        """
        graph = self._get_graph(tenant_id)
        
        query = """
        MATCH path = (start:Entity {id: $entity_id})-[*1..$depth]-(connected)
        WITH collect(path) as paths
        CALL {
            WITH paths
            UNWIND paths as p
            UNWIND nodes(p) as n
            RETURN collect(DISTINCT n) as nodes
        }
        CALL {
            WITH paths
            UNWIND paths as p
            UNWIND relationships(p) as r
            RETURN collect(DISTINCT r) as edges
        }
        RETURN nodes, edges
        """
        
        result = graph.query(
            query,
            params={
                "entity_id": entity_id,
                "depth": depth,
            },
        )
        
        nodes = []
        edges = []
        
        if result.result_set:
            row = result.result_set[0]
            nodes = [
                {
                    "id": n.properties.get("id"),
                    "name": n.properties.get("name"),
                    "type": n.properties.get("type"),
                    "labels": list(n.labels),
                }
                for n in row[0]
            ]
            edges = [
                {
                    "id": e.properties.get("id"),
                    "source": e.src_node,
                    "target": e.dest_node,
                    "type": e.properties.get("type"),
                }
                for e in row[1]
            ]
        
        return {"nodes": nodes, "edges": edges}

    async def find_entities_by_name(
        self,
        tenant_id: str,
        name_pattern: str,
        entity_type: str | None = None,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """
        Find entities by name pattern.
        
        Args:
            tenant_id: Tenant identifier
            name_pattern: Name to search (supports CONTAINS)
            entity_type: Optional type filter
            limit: Maximum results
            
        Returns:
            List of matching entities
        """
        graph = self._get_graph(tenant_id)
        
        if entity_type:
            query = """
            MATCH (e:Entity)
            WHERE e.name CONTAINS $pattern AND e.type = $type
            RETURN e
            LIMIT $limit
            """
            params = {"pattern": name_pattern, "type": entity_type, "limit": limit}
        else:
            query = """
            MATCH (e:Entity)
            WHERE e.name CONTAINS $pattern
            RETURN e
            LIMIT $limit
            """
            params = {"pattern": name_pattern, "limit": limit}
        
        result = graph.query(query, params=params)
        
        return [
            {
                "id": row[0].properties.get("id"),
                "name": row[0].properties.get("name"),
                "type": row[0].properties.get("type"),
            }
            for row in result.result_set
        ]

    async def get_entity_documents(
        self,
        tenant_id: str,
        entity_id: str,
        limit: int = 20,
    ) -> list[str]:
        """
        Get documents that mention an entity.
        
        Args:
            tenant_id: Tenant identifier
            entity_id: Entity ID
            limit: Maximum documents
            
        Returns:
            List of document IDs
        """
        graph = self._get_graph(tenant_id)
        
        query = """
        MATCH (e:Entity {id: $entity_id})-[:MENTIONED_IN]->(d:Document)
        RETURN d.id as doc_id
        LIMIT $limit
        """
        
        result = graph.query(
            query,
            params={"entity_id": entity_id, "limit": limit},
        )
        
        return [row[0] for row in result.result_set]

    async def delete_document_entities(
        self,
        tenant_id: str,
        document_id: str,
    ) -> int:
        """
        Delete entity relationships for a document.
        
        Note: Doesn't delete entities themselves as they may be
        referenced by other documents.
        
        Args:
            tenant_id: Tenant identifier
            document_id: Document ID
            
        Returns:
            Number of relationships deleted
        """
        graph = self._get_graph(tenant_id)
        
        query = """
        MATCH (e:Entity)-[r:MENTIONED_IN]->(d:Document {id: $doc_id})
        DELETE r
        RETURN count(r) as deleted
        """
        
        result = graph.query(query, params={"doc_id": document_id})
        
        deleted = result.result_set[0][0] if result.result_set else 0
        
        logger.info(
            "Document entity links deleted",
            tenant_id=tenant_id,
            document_id=document_id,
            deleted=deleted,
        )
        
        return deleted

    async def get_graph_stats(self, tenant_id: str) -> dict[str, int]:
        """
        Get graph statistics.
        
        Args:
            tenant_id: Tenant identifier
            
        Returns:
            Dict with entity/relationship counts
        """
        graph = self._get_graph(tenant_id)
        
        try:
            entity_result = graph.query("MATCH (e:Entity) RETURN count(e)")
            doc_result = graph.query("MATCH (d:Document) RETURN count(d)")
            rel_result = graph.query("MATCH ()-[r]->() RETURN count(r)")
            
            return {
                "entities": entity_result.result_set[0][0] if entity_result.result_set else 0,
                "documents": doc_result.result_set[0][0] if doc_result.result_set else 0,
                "relationships": rel_result.result_set[0][0] if rel_result.result_set else 0,
            }
        except Exception:
            return {"entities": 0, "documents": 0, "relationships": 0}

    def close(self) -> None:
        """Close the client connection."""
        # FalkorDB client manages connection internally
        pass
