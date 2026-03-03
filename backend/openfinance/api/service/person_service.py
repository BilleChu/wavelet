"""
Person Service Module.

Provides person-related services:
- Score calculation
- Activity aggregation
- Data extraction from existing sources
"""

from datetime import datetime, date, timedelta
from typing import Any, Optional
from uuid import uuid4
import logging
import json

from sqlalchemy import select, func, or_, and_
from sqlalchemy.ext.asyncio import AsyncSession

from openfinance.datacenter.models.orm import (
    EntityModel,
    RelationModel,
    PersonProfileModel,
    PersonActivityModel,
    PersonIndustryScoreModel,
    PersonScoreHistoryModel,
    PersonMentionModel,
    ResearchReportModel,
    ResearchAnalystModel,
    NewsModel,
)
from openfinance.infrastructure.logging.logging_config import get_logger

logger = get_logger(__name__)


class PersonScoreCalculator:
    """Person score calculation service."""
    
    MAX_INFLUENCE_SCORE = 30.0
    MAX_ACTIVITY_SCORE = 20.0
    MAX_ACCURACY_SCORE = 15.0
    MAX_NETWORK_SCORE = 10.0
    MAX_INDUSTRY_SCORE = 25.0
    
    async def calculate_score(
        self, 
        entity_id: str, 
        db: AsyncSession,
        industry: str | None = None
    ) -> dict[str, float]:
        """
        Calculate person score.
        
        Returns dict with all score dimensions.
        """
        influence = await self._calculate_influence_score(entity_id, db)
        activity = await self._calculate_activity_score(entity_id, db)
        accuracy = await self._calculate_accuracy_score(entity_id, db)
        network = await self._calculate_network_score(entity_id, db)
        industry_score = await self._calculate_industry_score(entity_id, db, industry)
        
        total = influence + activity + accuracy + network + industry_score
        
        return {
            "total_score": round(total, 2),
            "influence_score": round(influence, 2),
            "activity_score": round(activity, 2),
            "accuracy_score": round(accuracy, 2),
            "network_score": round(network, 2),
            "industry_score": round(industry_score, 2),
        }
    
    async def _calculate_influence_score(self, entity_id: str, db: AsyncSession) -> float:
        """Calculate influence score (max 30)."""
        score = 0.0
        
        profile = await db.scalar(
            select(PersonProfileModel).where(PersonProfileModel.entity_id == entity_id)
        )
        
        if profile:
            if profile.followers_count > 0:
                if profile.followers_count >= 100000:
                    score += 15
                elif profile.followers_count >= 50000:
                    score += 12
                elif profile.followers_count >= 10000:
                    score += 8
                elif profile.followers_count >= 1000:
                    score += 4
                else:
                    score += 2
            
            if profile.news_mentions > 0:
                if profile.news_mentions >= 100:
                    score += 10
                elif profile.news_mentions >= 50:
                    score += 7
                elif profile.news_mentions >= 20:
                    score += 4
                else:
                    score += 2
            
            if profile.report_count > 0:
                if profile.report_count >= 50:
                    score += 5
                elif profile.report_count >= 20:
                    score += 3
                else:
                    score += 1
        
        return min(score, self.MAX_INFLUENCE_SCORE)
    
    async def _calculate_activity_score(self, entity_id: str, db: AsyncSession) -> float:
        """Calculate activity score (max 20)."""
        score = 0.0
        
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        
        recent_activities = await db.scalar(
            select(func.count()).select_from(PersonActivityModel).where(
                PersonActivityModel.entity_id == entity_id,
                PersonActivityModel.activity_date >= thirty_days_ago
            )
        ) or 0
        
        if recent_activities >= 20:
            score += 10
        elif recent_activities >= 10:
            score += 7
        elif recent_activities >= 5:
            score += 4
        elif recent_activities >= 1:
            score += 2
        
        ninety_days_ago = datetime.utcnow() - timedelta(days=90)
        quarterly_activities = await db.scalar(
            select(func.count()).select_from(PersonActivityModel).where(
                PersonActivityModel.entity_id == entity_id,
                PersonActivityModel.activity_date >= ninety_days_ago
            )
        ) or 0
        
        if quarterly_activities >= 30:
            score += 10
        elif quarterly_activities >= 15:
            score += 6
        elif quarterly_activities >= 5:
            score += 3
        
        return min(score, self.MAX_ACTIVITY_SCORE)
    
    async def _calculate_accuracy_score(self, entity_id: str, db: AsyncSession) -> float:
        """Calculate accuracy score (max 15)."""
        score = 0.0
        
        profile = await db.scalar(
            select(PersonProfileModel).where(PersonProfileModel.entity_id == entity_id)
        )
        
        if profile and profile.properties:
            props = profile.properties
            accuracy_rate = props.get("prediction_accuracy")
            
            if accuracy_rate:
                if accuracy_rate >= 0.8:
                    score += 10
                elif accuracy_rate >= 0.6:
                    score += 7
                elif accuracy_rate >= 0.5:
                    score += 4
                else:
                    score += 2
            
            consistency = props.get("view_consistency")
            if consistency:
                if consistency >= 0.8:
                    score += 5
                elif consistency >= 0.6:
                    score += 3
                else:
                    score += 1
        
        return min(score, self.MAX_ACCURACY_SCORE)
    
    async def _calculate_network_score(self, entity_id: str, db: AsyncSession) -> float:
        """Calculate network score (max 10)."""
        score = 0.0
        
        relations_count = await db.scalar(
            select(func.count()).select_from(RelationModel).where(
                or_(
                    RelationModel.source_entity_id == entity_id,
                    RelationModel.target_entity_id == entity_id
                )
            )
        ) or 0
        
        if relations_count >= 50:
            score += 5
        elif relations_count >= 20:
            score += 3
        elif relations_count >= 10:
            score += 2
        elif relations_count >= 1:
            score += 1
        
        entity = await db.scalar(
            select(EntityModel).where(EntityModel.entity_id == entity_id)
        )
        
        if entity and entity.properties:
            props = entity.properties
            focus_industries = props.get("focus_industries", [])
            if len(focus_industries) >= 3:
                score += 3
            elif len(focus_industries) >= 1:
                score += 1
            
            certifications = props.get("certifications", [])
            if len(certifications) >= 2:
                score += 2
            elif len(certifications) >= 1:
                score += 1
        
        return min(score, self.MAX_NETWORK_SCORE)
    
    async def _calculate_industry_score(
        self, 
        entity_id: str, 
        db: AsyncSession,
        specific_industry: str | None = None
    ) -> float:
        """Calculate industry-specific score (max 25)."""
        score = 0.0
        
        if specific_industry:
            industry_score = await db.scalar(
                select(PersonIndustryScoreModel).where(
                    PersonIndustryScoreModel.entity_id == entity_id,
                    PersonIndustryScoreModel.industry == specific_industry
                ).order_by(PersonIndustryScoreModel.score_date.desc())
            )
            
            if industry_score:
                return min(industry_score.total_score or 0, self.MAX_INDUSTRY_SCORE)
        
        entity = await db.scalar(
            select(EntityModel).where(EntityModel.entity_id == entity_id)
        )
        
        if entity and entity.properties:
            props = entity.properties
            work_history = props.get("work_history", [])
            
            if work_history:
                years = sum(
                    w.get("years", 0) for w in work_history if isinstance(w, dict)
                )
                if years >= 15:
                    score += 10
                elif years >= 10:
                    score += 7
                elif years >= 5:
                    score += 4
                else:
                    score += 2
            
            focus_industries = props.get("focus_industries", [])
            if focus_industries:
                max_weight = max(
                    (fi.get("weight", 0) for fi in focus_industries if isinstance(fi, dict)),
                    default=0
                )
                if max_weight >= 0.8:
                    score += 8
                elif max_weight >= 0.5:
                    score += 5
                elif max_weight >= 0.3:
                    score += 3
        
        profile = await db.scalar(
            select(PersonProfileModel).where(PersonProfileModel.entity_id == entity_id)
        )
        
        if profile and profile.industry_scores:
            max_industry = max(
                (s.get("total_score", 0) for s in profile.industry_scores.values()),
                default=0
            )
            score = max(score, min(max_industry, 7))
        
        return min(score, self.MAX_INDUSTRY_SCORE)


class PersonActivityAggregator:
    """Person activity aggregation service."""
    
    async def aggregate_activities(
        self,
        entity_id: str,
        db: AsyncSession,
        days: int = 30
    ) -> list[dict[str, Any]]:
        """Aggregate person activities from various sources."""
        activities = []
        
        news_activities = await self._aggregate_from_news(entity_id, db, days)
        activities.extend(news_activities)
        
        report_activities = await self._aggregate_from_reports(entity_id, db, days)
        activities.extend(report_activities)
        
        activities.sort(key=lambda x: x.get("activity_date") or "", reverse=True)
        
        return activities
    
    async def _aggregate_from_news(
        self,
        entity_id: str,
        db: AsyncSession,
        days: int
    ) -> list[dict[str, Any]]:
        """Aggregate activities from news mentions."""
        activities = []
        
        mentions = await db.execute(
            select(PersonMentionModel).where(
                PersonMentionModel.entity_id == entity_id,
                PersonMentionModel.mention_type == "news",
                PersonMentionModel.mention_date >= datetime.utcnow() - timedelta(days=days)
            ).order_by(PersonMentionModel.mention_date.desc())
        )
        
        for mention in mentions.scalars():
            activities.append({
                "activity_id": f"news_{mention.id}",
                "activity_type": "news",
                "title": mention.title,
                "summary": mention.summary,
                "source_url": mention.source_url,
                "sentiment_score": float(mention.sentiment_score) if mention.sentiment_score else None,
                "related_codes": mention.related_codes or [],
                "related_industries": mention.related_industries or [],
                "activity_date": mention.mention_date.isoformat() if mention.mention_date else None,
            })
        
        return activities
    
    async def _aggregate_from_reports(
        self,
        entity_id: str,
        db: AsyncSession,
        days: int
    ) -> list[dict[str, Any]]:
        """Aggregate activities from research reports."""
        activities = []
        
        entity = await db.scalar(
            select(EntityModel).where(EntityModel.entity_id == entity_id)
        )
        
        if not entity:
            return activities
        
        person_name = entity.name
        
        reports = await db.execute(
            select(ResearchReportModel).where(
                ResearchReportModel.analyst == person_name,
                ResearchReportModel.publish_date >= datetime.utcnow() - timedelta(days=days)
            ).order_by(ResearchReportModel.publish_date.desc())
        )
        
        for report in reports.scalars():
            activities.append({
                "activity_id": f"report_{report.id}",
                "activity_type": "report",
                "title": report.title,
                "summary": report.summary,
                "source": report.institution,
                "source_url": report.source_url,
                "related_codes": [report.code] if report.code else [],
                "activity_date": report.publish_date.isoformat() if report.publish_date else None,
            })
        
        return activities


class PersonDataService:
    """Person data management service."""
    
    def __init__(self):
        self.score_calculator = PersonScoreCalculator()
        self.activity_aggregator = PersonActivityAggregator()
    
    async def create_person_from_analyst(
        self,
        analyst: ResearchAnalystModel,
        db: AsyncSession
    ) -> EntityModel:
        """Create person entity from analyst data."""
        entity_id = f"person_{analyst.analyst_id}"
        
        existing = await db.scalar(
            select(EntityModel).where(EntityModel.entity_id == entity_id)
        )
        
        if existing:
            return existing
        
        entity = EntityModel(
            id=str(uuid4()),
            entity_id=entity_id,
            entity_type="person",
            name=analyst.name,
            properties={
                "person_type": "analyst",
                "company": analyst.institution,
                "certifications": [],
                "focus_industries": [{"industry": analyst.specialty, "weight": 1.0}] if analyst.specialty else [],
            },
            source="research_analyst",
        )
        
        db.add(entity)
        
        profile = PersonProfileModel(
            id=str(uuid4()),
            entity_id=entity_id,
            report_count=analyst.report_count,
            accuracy_score=float(analyst.accuracy_score) if analyst.accuracy_score else 0,
        )
        db.add(profile)
        
        await db.flush()
        
        return entity
    
    async def create_person_from_report(
        self,
        report: ResearchReportModel,
        db: AsyncSession
    ) -> EntityModel | None:
        """Create person entity from report analyst."""
        if not report.analyst:
            return None
        
        entity_id = f"person_analyst_{report.analyst}_{report.institution or 'unknown'}"
        entity_id = entity_id.replace(" ", "_").lower()[:100]
        
        existing = await db.scalar(
            select(EntityModel).where(EntityModel.entity_id == entity_id)
        )
        
        if existing:
            return existing
        
        entity = EntityModel(
            id=str(uuid4()),
            entity_id=entity_id,
            entity_type="person",
            name=report.analyst,
            properties={
                "person_type": "analyst",
                "company": report.institution,
            },
            source="research_report",
        )
        
        db.add(entity)
        
        profile = PersonProfileModel(
            id=str(uuid4()),
            entity_id=entity_id,
            report_count=1,
        )
        db.add(profile)
        
        await db.flush()
        
        return entity
    
    async def update_person_scores(
        self,
        entity_id: str,
        db: AsyncSession
    ) -> dict[str, float]:
        """Update person scores and save history."""
        scores = await self.score_calculator.calculate_score(entity_id, db)
        
        profile = await db.scalar(
            select(PersonProfileModel).where(PersonProfileModel.entity_id == entity_id)
        )
        
        if profile:
            profile.total_score = scores["total_score"]
            profile.influence_score = scores["influence_score"]
            profile.activity_score = scores["activity_score"]
            profile.accuracy_score = scores["accuracy_score"]
            profile.network_score = scores["network_score"]
            profile.industry_score = scores["industry_score"]
            profile.last_synced_at = datetime.utcnow()
        else:
            profile = PersonProfileModel(
                id=str(uuid4()),
                entity_id=entity_id,
                **scores,
            )
            db.add(profile)
        
        history = PersonScoreHistoryModel(
            id=str(uuid4()),
            entity_id=entity_id,
            score_date=date.today(),
            **scores,
        )
        db.add(history)
        
        await db.flush()
        
        return scores
    
    async def sync_analysts_from_reports(
        self,
        db: AsyncSession,
        limit: int = 100
    ) -> int:
        """Sync person entities from research reports."""
        reports = await db.execute(
            select(ResearchReportModel)
            .where(ResearchReportModel.analyst.isnot(None))
            .distinct(ResearchReportModel.analyst, ResearchReportModel.institution)
            .limit(limit)
        )
        
        created = 0
        for report in reports.scalars():
            try:
                entity = await self.create_person_from_report(report, db)
                if entity:
                    created += 1
            except Exception as e:
                logger.warning(f"Failed to create person from report: {e}")
                continue
        
        await db.commit()
        
        return created
    
    async def update_all_scores(
        self,
        db: AsyncSession,
        batch_size: int = 50
    ) -> int:
        """Update scores for all person entities."""
        persons = await db.execute(
            select(EntityModel.entity_id).where(EntityModel.entity_type == "person")
        )
        
        updated = 0
        for (entity_id,) in persons.all():
            try:
                await self.update_person_scores(entity_id, db)
                updated += 1
                
                if updated % batch_size == 0:
                    await db.commit()
            except Exception as e:
                logger.warning(f"Failed to update scores for {entity_id}: {e}")
                continue
        
        await db.commit()
        
        return updated
