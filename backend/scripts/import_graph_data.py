"""
Import knowledge graph data from JSON file to database.
"""

import asyncio
import json
import uuid
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from openfinance.datacenter.database import async_session_maker
from openfinance.datacenter.models import EntityModel, RelationModel


async def import_graph_data(json_path: str, clear_existing: bool = False):
    """Import graph data from JSON file."""
    
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    entities = data.get('entities', [])
    relations = data.get('relations', [])
    
    print(f"Loading {len(entities)} entities and {len(relations)} relations...")
    
    async with async_session_maker() as session:
        if clear_existing:
            print("Clearing existing data...")
            await session.execute("DELETE FROM openfinance.relations")
            await session.execute("DELETE FROM openfinance.entities")
            await session.commit()
        
        entity_id_map = {}
        
        for entity_data in entities:
            entity_key = entity_data.get('entity_key')
            entity_type = entity_data.get('entity_type')
            name = entity_data.get('name')
            
            if not entity_key or not entity_type or not name:
                print(f"Skipping invalid entity: {entity_data}")
                continue
            
            existing_query = select(EntityModel).where(EntityModel.entity_id == entity_key)
            existing_result = await session.execute(existing_query)
            existing = existing_result.scalar_one_or_none()
            
            if existing:
                entity_id_map[entity_key] = existing.entity_id
                print(f"Entity already exists: {name} ({entity_key})")
                continue
            
            entity_id = entity_key
            entity_id_map[entity_key] = entity_id
            
            entity = EntityModel(
                id=str(uuid.uuid4()),
                entity_id=entity_id,
                entity_type=entity_type,
                name=name,
                code=entity_data.get('code'),
                properties=entity_data.get('properties', {}),
                source=entity_data.get('source', 'import'),
                confidence=entity_data.get('confidence', 1.0),
            )
            
            session.add(entity)
            print(f"Added entity: {name} ({entity_type})")
        
        await session.commit()
        
        for rel_data in relations:
            source_key = rel_data.get('source')
            target_key = rel_data.get('target')
            rel_type = rel_data.get('type')
            
            if not source_key or not target_key or not rel_type:
                print(f"Skipping invalid relation: {rel_data}")
                continue
            
            source_id = entity_id_map.get(source_key)
            target_id = entity_id_map.get(target_key)
            
            if not source_id or not target_id:
                print(f"Skipping relation with missing entity: {source_key} -> {target_key}")
                continue
            
            existing_query = select(RelationModel).where(
                RelationModel.source_entity_id == source_id,
                RelationModel.target_entity_id == target_id,
                RelationModel.relation_type == rel_type,
            )
            existing_result = await session.execute(existing_query)
            existing = existing_result.scalar_one_or_none()
            
            if existing:
                print(f"Relation already exists: {source_key} -[{rel_type}]-> {target_key}")
                continue
            
            relation_id = f"rel_{uuid.uuid4().hex[:8]}"
            
            relation = RelationModel(
                id=str(uuid.uuid4()),
                relation_id=relation_id,
                source_entity_id=source_id,
                target_entity_id=target_id,
                relation_type=rel_type,
                weight=rel_data.get('weight', 1.0),
                confidence=rel_data.get('confidence', 1.0),
                properties=rel_data.get('properties', {}),
                source=rel_data.get('source', 'import'),
            )
            
            session.add(relation)
            print(f"Added relation: {source_key} -[{rel_type}]-> {target_key}")
        
        await session.commit()
    
    print(f"\nImport complete!")
    print(f"  Entities: {len(entity_id_map)}")
    print(f"  Relations: {len(relations)}")


if __name__ == "__main__":
    import sys
    
    json_path = sys.argv[1] if len(sys.argv) > 1 else "data/knowledge_graph/company_graph_20260217.json"
    clear = "--clear" in sys.argv
    
    asyncio.run(import_graph_data(json_path, clear))
