"""
Data Service Versioning Module.

Provides API version management and deprecation handling.
"""

import logging
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class VersionStatus(str, Enum):
    """API version status."""

    CURRENT = "current"
    DEPRECATED = "deprecated"
    SUNSET = "sunset"
    RETIRED = "retired"


class APIVersion(BaseModel):
    """API version information."""

    version: str = Field(..., description="Version string (e.g., '1.0.0')")
    status: VersionStatus = Field(default=VersionStatus.CURRENT, description="Version status")
    release_date: datetime = Field(..., description="Release date")
    deprecation_date: datetime | None = Field(default=None, description="Deprecation date")
    sunset_date: datetime | None = Field(default=None, description="Sunset date")
    release_notes: str | None = Field(default=None, description="Release notes")
    breaking_changes: list[str] = Field(default_factory=list, description="Breaking changes")
    migration_guide: str | None = Field(default=None, description="Migration guide URL")


class DeprecationNotice(BaseModel):
    """Deprecation notice for an endpoint."""

    endpoint: str = Field(..., description="Endpoint path")
    method: str = Field(..., description="HTTP method")
    deprecated_since: str = Field(..., description="Deprecated since version")
    removal_version: str | None = Field(default=None, description="Planned removal version")
    removal_date: datetime | None = Field(default=None, description="Planned removal date")
    replacement: str | None = Field(default=None, description="Replacement endpoint")
    migration_steps: list[str] = Field(default_factory=list, description="Migration steps")


class VersionManager:
    """
    Manages API versioning and deprecation.
    
    Provides:
    - Version registration and tracking
    - Deprecation notices
    - Version routing
    - Sunset header management
    """

    def __init__(self) -> None:
        self._versions: dict[str, APIVersion] = {}
        self._deprecations: list[DeprecationNotice] = []
        self._current_version: str | None = None
        self._supported_versions: list[str] = []

    def register_version(
        self,
        version: str,
        release_date: datetime,
        release_notes: str | None = None,
        breaking_changes: list[str] | None = None,
    ) -> APIVersion:
        """Register a new API version."""
        api_version = APIVersion(
            version=version,
            status=VersionStatus.CURRENT,
            release_date=release_date,
            release_notes=release_notes,
            breaking_changes=breaking_changes or [],
        )
        
        if self._current_version:
            old_version = self._versions.get(self._current_version)
            if old_version:
                old_version.status = VersionStatus.DEPRECATED
                old_version.deprecation_date = datetime.now()
        
        self._versions[version] = api_version
        self._current_version = version
        self._supported_versions.append(version)
        
        logger.info(f"Registered API version {version}")
        return api_version

    def deprecate_version(
        self,
        version: str,
        sunset_days: int = 180,
    ) -> bool:
        """Deprecate a version with sunset period."""
        if version not in self._versions:
            return False
        
        api_version = self._versions[version]
        api_version.status = VersionStatus.DEPRECATED
        api_version.deprecation_date = datetime.now()
        api_version.sunset_date = datetime.now() + timedelta(days=sunset_days)
        
        logger.warning(
            f"Deprecated API version {version}. "
            f"Sunset date: {api_version.sunset_date}"
        )
        return True

    def deprecate_endpoint(
        self,
        endpoint: str,
        method: str,
        deprecated_since: str,
        removal_version: str | None = None,
        replacement: str | None = None,
        migration_steps: list[str] | None = None,
    ) -> DeprecationNotice:
        """Deprecate an endpoint."""
        notice = DeprecationNotice(
            endpoint=endpoint,
            method=method,
            deprecated_since=deprecated_since,
            removal_version=removal_version,
            replacement=replacement,
            migration_steps=migration_steps or [],
        )
        
        self._deprecations.append(notice)
        logger.warning(f"Deprecated endpoint {method} {endpoint}")
        return notice

    def get_version(self, version: str) -> APIVersion | None:
        """Get version information."""
        return self._versions.get(version)

    def get_current_version(self) -> APIVersion | None:
        """Get current API version."""
        if self._current_version:
            return self._versions.get(self._current_version)
        return None

    def get_supported_versions(self) -> list[APIVersion]:
        """Get all supported versions."""
        return [
            self._versions[v]
            for v in self._supported_versions
            if v in self._versions
        ]

    def get_deprecations(self, endpoint: str | None = None) -> list[DeprecationNotice]:
        """Get deprecation notices."""
        if endpoint:
            return [d for d in self._deprecations if d.endpoint == endpoint]
        return self._deprecations

    def is_version_supported(self, version: str) -> bool:
        """Check if a version is supported."""
        if version not in self._versions:
            return False
        
        api_version = self._versions[version]
        return api_version.status in (
            VersionStatus.CURRENT,
            VersionStatus.DEPRECATED,
        )

    def get_sunset_header(self, version: str) -> str | None:
        """Get sunset header value for a version."""
        api_version = self._versions.get(version)
        if api_version and api_version.sunset_date:
            return api_version.sunset_date.strftime("%a, %d %b %Y %H:%M:%S GMT")
        return None

    def get_deprecation_headers(self, endpoint: str, method: str) -> dict[str, str]:
        """Get deprecation headers for an endpoint."""
        headers = {}
        
        for notice in self._deprecations:
            if notice.endpoint == endpoint and notice.method == method:
                headers["Deprecation"] = "true"
                
                if notice.removal_date:
                    headers["Sunset"] = notice.removal_date.strftime(
                        "%a, %d %b %Y %H:%M:%S GMT"
                    )
                
                if notice.replacement:
                    headers["Link"] = f'<{notice.replacement}>; rel="successor-version"'
                
                break
        
        return headers

    def get_version_info_response(self) -> dict[str, Any]:
        """Get version info for API response."""
        current = self.get_current_version()
        
        return {
            "current_version": current.version if current else None,
            "supported_versions": [v.version for v in self.get_supported_versions()],
            "deprecations": [
                {
                    "endpoint": d.endpoint,
                    "method": d.method,
                    "deprecated_since": d.deprecated_since,
                    "replacement": d.replacement,
                }
                for d in self._deprecations
            ],
        }


_version_manager: VersionManager | None = None


def get_version_manager() -> VersionManager:
    """Get the global version manager instance."""
    global _version_manager
    if _version_manager is None:
        _version_manager = VersionManager()
        _version_manager.register_version(
            version="1.0.0",
            release_date=datetime(2024, 1, 1),
            release_notes="Initial release of Data Service API",
        )
    return _version_manager
