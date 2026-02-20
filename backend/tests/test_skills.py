"""Tests for the agent skills system."""

import pytest
from pathlib import Path
import tempfile

from openfinance.agents.skills.loader import SkillsLoader
from openfinance.agents.skills.registry import SkillRegistry
from openfinance.agents.skills.base import SkillMetadata, SkillInfo


class TestSkillsLoader:
    """Tests for SkillsLoader."""
    
    @pytest.fixture
    def temp_workspace(self):
        """Create a temporary workspace for testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)
    
    @pytest.fixture
    def loader(self, temp_workspace):
        """Create a SkillsLoader instance."""
        return SkillsLoader(temp_workspace)
    
    def test_list_builtin_skills(self, loader):
        """Test listing builtin skills."""
        skills = loader.list_skills(filter_unavailable=False)
        
        assert len(skills) > 0
        
        skill_names = [s.name for s in skills]
        assert "buffett-investment" in skill_names
    
    def test_load_skill_content(self, loader):
        """Test loading skill content."""
        content = loader.load_skill("buffett-investment")
        
        assert content is not None
        assert "buffett" in content.lower()
        assert "moat" in content.lower()
    
    def test_build_skills_summary(self, loader):
        """Test building skills summary."""
        summary = loader.build_skills_summary()
        
        assert "<skills>" in summary
        assert "</skills>" in summary
        assert "buffett-investment" in summary
    
    def test_parse_frontmatter(self, loader):
        """Test parsing YAML frontmatter."""
        content = """---
name: test-skill
description: A test skill
homepage: https://example.com
---
# Test Skill Content
"""
        metadata = loader._parse_frontmatter(content)
        
        assert metadata is not None
        assert metadata.name == "test-skill"
        assert metadata.description == "A test skill"
        assert metadata.homepage == "https://example.com"
    
    def test_strip_frontmatter(self, loader):
        """Test stripping frontmatter from content."""
        content = """---
name: test-skill
description: A test skill
---
# Test Skill Content

This is the actual content.
"""
        stripped = loader._strip_frontmatter(content)
        
        assert "---" not in stripped
        assert "# Test Skill Content" in stripped
        assert "This is the actual content." in stripped
    
    def test_load_skills_for_context(self, loader):
        """Test loading skills for context."""
        content = loader.load_skills_for_context(["buffett-investment"])
        
        assert "### Skill: buffett-investment" in content
        assert "Moat Analysis" in content


class TestSkillRegistry:
    """Tests for SkillRegistry."""
    
    @pytest.fixture
    def temp_workspace(self):
        """Create a temporary workspace for testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)
    
    @pytest.fixture
    def registry(self, temp_workspace):
        """Create a SkillRegistry instance."""
        return SkillRegistry(temp_workspace)
    
    def test_list_skills(self, registry):
        """Test listing skills through registry."""
        skills = registry.list_skills()
        
        assert len(skills) > 0
    
    def test_get_skill(self, registry):
        """Test getting a specific skill."""
        skill = registry.get_skill("buffett-investment")
        
        assert skill is not None
        assert skill.name == "buffett-investment"
    
    def test_has_skill(self, registry):
        """Test checking if skill exists."""
        assert registry.has_skill("buffett-investment") is True
        assert registry.has_skill("nonexistent-skill") is False
    
    def test_get_skill_names(self, registry):
        """Test getting all skill names."""
        names = registry.get_skill_names()
        
        assert "buffett-investment" in names
    
    def test_register_handler(self, registry):
        """Test registering a skill handler."""
        def test_handler(context):
            return "test result"
        
        registry.register_handler("test-skill", test_handler)
        
        handler = registry.get_handler("test-skill")
        assert handler == test_handler
    
    def test_get_stats(self, registry):
        """Test getting registry statistics."""
        stats = registry.get_stats()
        
        assert "total_skills" in stats
        assert "available_skills" in stats
        assert "registered_handlers" in stats
        assert stats["total_skills"] > 0


class TestSkillMetadata:
    """Tests for SkillMetadata."""
    
    def test_get_requires(self):
        """Test getting requirements."""
        metadata = SkillMetadata(
            name="test",
            description="test",
            metadata={
                "nanobot": {
                    "requires": {
                        "bins": ["python"],
                        "env": ["API_KEY"]
                    }
                }
            }
        )
        
        requires = metadata.get_requires()
        assert "bins" in requires
        assert "python" in requires["bins"]
        assert "env" in requires
        assert "API_KEY" in requires["env"]
    
    def test_is_always_load(self):
        """Test always load flag."""
        metadata_always = SkillMetadata(
            name="test",
            description="test",
            metadata={"nanobot": {"always": True}}
        )
        
        metadata_not_always = SkillMetadata(
            name="test",
            description="test",
            metadata={}
        )
        
        assert metadata_always.is_always_load() is True
        assert metadata_not_always.is_always_load() is False


class TestSkillInfo:
    """Tests for SkillInfo."""
    
    def test_to_xml(self):
        """Test XML conversion."""
        metadata = SkillMetadata(
            name="test-skill",
            description="A test skill for testing"
        )
        
        info = SkillInfo(
            name="test-skill",
            path=Path("/test/path"),
            source="builtin",
            metadata=metadata,
            available=True
        )
        
        xml = info.to_xml()
        
        assert '<skill available="true">' in xml
        assert "<name>test-skill</name>" in xml
        assert "<description>A test skill for testing</description>" in xml
        assert "<location>/test/path</location>" in xml
    
    def test_to_xml_unavailable(self):
        """Test XML conversion for unavailable skill."""
        info = SkillInfo(
            name="test-skill",
            path=Path("/test/path"),
            source="builtin",
            metadata=None,
            available=False,
            missing_requirements=["CLI: python", "ENV: API_KEY"]
        )
        
        xml = info.to_xml()
        
        assert '<skill available="false">' in xml
        assert "<requires>CLI: python, ENV: API_KEY</requires>" in xml
