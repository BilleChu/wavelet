"""
Configuration-Driven Collector Framework.

Provides a base class for collectors that can be configured via
YAML/JSON configuration files, eliminating the need for custom
collector implementations for simple data sources.

Usage:
    from datacenter.core import ConfigDrivenCollector, CollectorConfig
    
    config = CollectorConfig.from_yaml("collectors/stock_quote.yaml")
    collector = ConfigDrivenCollector(config)
    data = await collector.collect()
"""

import asyncio
import hashlib
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, date
from enum import Enum
from pathlib import Path
from typing import Any, Callable

import yaml

from .converters import ValueConverter, DateConverter
from .code_utils import CodeUtils
from .http_client import HttpClient, HttpMethod, RetryPolicy, RateLimitPolicy
from .field_mapping import FieldMappingRegistry, FieldMapping, FieldType
from .config import SourceSettings
from ..collector import (
    BaseCollector,
    CollectionConfig,
    CollectionResult,
    DataSource,
    DataType,
    DataFrequency,
)

logger = logging.getLogger(__name__)


class RequestType(str, Enum):
    """HTTP request types."""
    GET = "GET"
    POST = "POST"


class AuthType(str, Enum):
    """Authentication types."""
    NONE = "none"
    API_KEY = "api_key"
    BEARER = "bearer"
    CUSTOM = "custom"


@dataclass
class RequestConfig:
    """
    HTTP request configuration.
    
    Attributes:
        method: HTTP method
        url: Request URL (can contain placeholders)
        headers: Request headers
        params: Query parameters
        body: Request body (for POST)
        timeout: Request timeout
    """
    method: RequestType = RequestType.GET
    url: str = ""
    headers: dict[str, str] = field(default_factory=dict)
    params: dict[str, Any] = field(default_factory=dict)
    body: dict[str, Any] | None = None
    timeout: float = 30.0


@dataclass
class AuthConfig:
    """
    Authentication configuration.
    
    Attributes:
        type: Authentication type
        api_key: API key value or env var reference
        header_name: Header name for API key
        prefix: Prefix for auth header (e.g., "Bearer")
    """
    type: AuthType = AuthType.NONE
    api_key: str | None = None
    header_name: str = "Authorization"
    prefix: str | None = None
    
    def apply(self, headers: dict[str, str], settings: SourceSettings | None = None) -> dict[str, str]:
        """Apply authentication to headers."""
        result = dict(headers)
        
        if self.type == AuthType.NONE:
            return result
        
        key = self._resolve_api_key(settings)
        if not key:
            return result
        
        if self.type == AuthType.API_KEY:
            result[self.header_name] = key
        elif self.type == AuthType.BEARER:
            result[self.header_name] = f"Bearer {key}"
        elif self.type == AuthType.CUSTOM:
            if self.prefix:
                result[self.header_name] = f"{self.prefix} {key}"
            else:
                result[self.header_name] = key
        
        return result
    
    def _resolve_api_key(self, settings: SourceSettings | None = None) -> str | None:
        """Resolve API key from config or settings."""
        import os
        
        if settings and settings.api_key:
            return settings.resolve_api_key()
        
        if not self.api_key:
            return None
        
        if self.api_key.startswith("${") and self.api_key.endswith("}"):
            env_var = self.api_key[2:-1]
            return os.environ.get(env_var)
        
        if self.api_key.startswith("$"):
            env_var = self.api_key[1:]
            return os.environ.get(env_var)
        
        return self.api_key


@dataclass
class ResponseParserConfig:
    """
    Response parser configuration.
    
    Attributes:
        data_path: JSONPath to data array in response
        total_path: JSONPath to total count
        error_path: JSONPath to error message
        error_check: Expression to check for errors
    """
    data_path: str = ""
    total_path: str | None = None
    error_path: str | None = None
    error_check: str | None = None
    
    def parse(self, response: dict[str, Any]) -> list[dict[str, Any]]:
        """Parse response to extract data array."""
        if not self.data_path:
            if isinstance(response, list):
                return response
            if isinstance(response, dict):
                for key in ["data", "items", "results", "list"]:
                    if key in response and isinstance(response[key], list):
                        return response[key]
            return [response] if response else []
        
        data = response
        for part in self.data_path.split("."):
            if isinstance(data, dict) and part in data:
                data = data[part]
            elif isinstance(data, list) and part.isdigit():
                data = data[int(part)]
            else:
                return []
        
        if isinstance(data, list):
            return data
        return [data] if data else []


@dataclass
class CollectorConfig:
    """
    Complete collector configuration.
    
    This configuration can be loaded from YAML/JSON files,
    enabling declarative collector definitions.
    """
    collector_id: str
    name: str
    source: DataSource
    data_type: DataType
    frequency: DataFrequency = DataFrequency.DAILY
    
    request: RequestConfig = field(default_factory=RequestConfig)
    auth: AuthConfig = field(default_factory=AuthConfig)
    parser: ResponseParserConfig = field(default_factory=ResponseParserConfig)
    
    field_mapping: dict[str, str | dict[str, Any]] = field(default_factory=dict)
    required_fields: list[str] = field(default_factory=list)
    
    dedup_keys: list[str] = field(default_factory=lambda: ["code", "trade_date"])
    dedup_enabled: bool = True
    
    rate_limit: float = 10.0
    max_retries: int = 3
    retry_delay: float = 1.0
    
    metadata: dict[str, Any] = field(default_factory=dict)
    
    @classmethod
    def from_yaml(cls, path: str | Path) -> "CollectorConfig":
        """Load configuration from YAML file."""
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        return cls.from_dict(data)
    
    @classmethod
    def from_json(cls, path: str | Path) -> "CollectorConfig":
        """Load configuration from JSON file."""
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return cls.from_dict(data)
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CollectorConfig":
        """Create from dictionary."""
        request_data = data.get("request", {})
        request = RequestConfig(
            method=RequestType(request_data.get("method", "GET")),
            url=request_data.get("url", ""),
            headers=request_data.get("headers", {}),
            params=request_data.get("params", {}),
            body=request_data.get("body"),
            timeout=request_data.get("timeout", 30.0),
        )
        
        auth_data = data.get("auth", {})
        auth = AuthConfig(
            type=AuthType(auth_data.get("type", "none")),
            api_key=auth_data.get("api_key"),
            header_name=auth_data.get("header_name", "Authorization"),
            prefix=auth_data.get("prefix"),
        )
        
        parser_data = data.get("parser", {})
        parser = ResponseParserConfig(
            data_path=parser_data.get("data_path", ""),
            total_path=parser_data.get("total_path"),
            error_path=parser_data.get("error_path"),
            error_check=parser_data.get("error_check"),
        )
        
        source_val = data.get("source", "custom")
        source = source_val if isinstance(source_val, DataSource) else DataSource(source_val)
        
        data_type_val = data.get("data_type", "stock_quote")
        data_type = data_type_val if isinstance(data_type_val, DataType) else DataType(data_type_val)
        
        frequency_val = data.get("frequency", "daily")
        frequency = frequency_val if isinstance(frequency_val, DataFrequency) else DataFrequency(frequency_val)
        
        return cls(
            collector_id=data.get("collector_id", ""),
            name=data.get("name", ""),
            source=source,
            data_type=data_type,
            frequency=frequency,
            request=request,
            auth=auth,
            parser=parser,
            field_mapping=data.get("field_mapping", {}),
            required_fields=data.get("required_fields", []),
            dedup_keys=data.get("dedup_keys", ["code", "trade_date"]),
            dedup_enabled=data.get("dedup_enabled", True),
            rate_limit=data.get("rate_limit", 10.0),
            max_retries=data.get("max_retries", 3),
            retry_delay=data.get("retry_delay", 1.0),
            metadata=data.get("metadata", {}),
        )
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        source_value = self.source.value if hasattr(self.source, 'value') else str(self.source)
        data_type_value = self.data_type.value if hasattr(self.data_type, 'value') else str(self.data_type)
        frequency_value = self.frequency.value if hasattr(self.frequency, 'value') else str(self.frequency)
        
        return {
            "collector_id": self.collector_id,
            "name": self.name,
            "source": source_value,
            "data_type": data_type_value,
            "frequency": frequency_value,
            "request": {
                "method": self.request.method.value,
                "url": self.request.url,
                "headers": self.request.headers,
                "params": self.request.params,
                "timeout": self.request.timeout,
            },
            "auth": {
                "type": self.auth.type.value,
                "api_key": self.auth.api_key,
                "header_name": self.auth.header_name,
            },
            "parser": {
                "data_path": self.parser.data_path,
            },
            "field_mapping": self.field_mapping,
            "required_fields": self.required_fields,
            "dedup_keys": self.dedup_keys,
            "rate_limit": self.rate_limit,
            "max_retries": self.max_retries,
        }


class ConfigDrivenCollector(BaseCollector):
    """
    Configuration-driven data collector.
    
    This collector can be fully configured via YAML/JSON files,
    eliminating the need for custom Python code for most use cases.
    
    Features:
    - Declarative configuration
    - Automatic field mapping
    - Built-in retry and rate limiting
    - Response parsing
    - Data validation
    """
    
    def __init__(
        self,
        config: CollectorConfig,
        source_settings: SourceSettings | None = None,
        field_mapping_registry: FieldMappingRegistry | None = None,
    ) -> None:
        self.config = config
        self.source_settings = source_settings
        self._field_mapping_registry = field_mapping_registry or FieldMappingRegistry()
        
        self._setup_field_mapping()
        
        collection_config = CollectionConfig(
            source=config.source,
            data_type=config.data_type,
            frequency=config.frequency,
        )
        
        super().__init__(config=collection_config)
        
        self._http_client: HttpClient | None = None
        self._seen_hashes: set[str] = set()
    
    @property
    def source(self) -> DataSource:
        return self.config.source
    
    def _setup_field_mapping(self) -> None:
        """Setup field mapping from configuration."""
        mapping = FieldMapping(
            source=self.config.source.value,
            data_type=self.config.data_type.value,
        )
        
        for source_field, target_spec in self.config.field_mapping.items():
            if isinstance(target_spec, str):
                mapping.add_rule(
                    source_field=source_field,
                    target_field=target_spec,
                    field_type=FieldType.RAW,
                )
            elif isinstance(target_spec, dict):
                target_field = target_spec.get("target", source_field)
                field_type = FieldType(target_spec.get("type", "raw"))
                default = target_spec.get("default")
                converter_name = target_spec.get("converter")
                
                converter = self._get_converter(converter_name) if converter_name else None
                
                mapping.add_rule(
                    source_field=source_field,
                    target_field=target_field,
                    field_type=field_type,
                    default=default,
                    converter=converter,
                )
        
        self._field_mapping_registry.register(mapping)
    
    def _get_converter(self, name: str) -> Callable[[Any], Any] | None:
        """Get converter function by name."""
        converters = {
            "safe_float": ValueConverter.to_float,
            "safe_int": ValueConverter.to_int,
            "safe_str": ValueConverter.to_str,
            "to_date": DateConverter.to_date,
            "to_eastmoney_code": CodeUtils.to_eastmoney_format,
            "normalize_code": CodeUtils.normalize,
        }
        return converters.get(name)
    
    async def _initialize(self) -> None:
        """Initialize the collector."""
        retry_policy = RetryPolicy(
            max_retries=self.config.max_retries,
            base_delay=self.config.retry_delay,
        )
        
        rate_limit_policy = RateLimitPolicy(
            requests_per_second=self.config.rate_limit,
        )
        
        headers = dict(self.config.request.headers)
        headers = self.config.auth.apply(headers, self.source_settings)
        
        self._http_client = HttpClient(
            retry_policy=retry_policy,
            rate_limit_policy=rate_limit_policy,
            default_headers=headers,
            default_timeout=self.config.request.timeout,
        )
        
        await self._http_client.start()
    
    async def _cleanup(self) -> None:
        """Cleanup resources."""
        if self._http_client:
            await self._http_client.close()
    
    async def _collect(self, **kwargs: Any) -> list[Any]:
        """Execute data collection."""
        if not self._http_client:
            await self._initialize()
        
        url = self._build_url(**kwargs)
        params = self._build_params(**kwargs)
        headers = self._build_headers(**kwargs)
        
        if self.config.request.method == RequestType.GET:
            response = await self._http_client.get(
                url=url,
                params=params,
                headers=headers,
            )
        else:
            response = await self._http_client.post(
                url=url,
                json=self.config.request.body,
                headers=headers,
            )
        
        if not response.ok:
            raise Exception(f"Request failed: {response.status}")
        
        if not response.json:
            return []
        
        raw_data = self.config.parser.parse(response.json)
        
        mapped_data = self._field_mapping_registry.apply_batch(
            self.config.source.value,
            self.config.data_type.value,
            raw_data,
        )
        
        if self.config.dedup_enabled:
            mapped_data = self._deduplicate(mapped_data)
        
        validated_data = [
            record for record in mapped_data
            if self._validate_record(record)
        ]
        
        return validated_data
    
    def _build_url(self, **kwargs: Any) -> str:
        """Build request URL with placeholders resolved."""
        url = self.config.request.url
        
        for key, value in kwargs.items():
            placeholder = f"{{{key}}}"
            if placeholder in url:
                url = url.replace(placeholder, str(value))
        
        return url
    
    def _build_params(self, **kwargs: Any) -> dict[str, Any]:
        """Build request parameters."""
        params = dict(self.config.request.params)
        
        for key, value in kwargs.items():
            if key not in ("symbols", "start_date", "end_date"):
                params[key] = value
        
        if "symbols" in kwargs:
            params["symbols"] = ",".join(kwargs["symbols"]) if isinstance(kwargs["symbols"], list) else kwargs["symbols"]
        
        if "start_date" in kwargs:
            params["start_date"] = kwargs["start_date"]
        if "end_date" in kwargs:
            params["end_date"] = kwargs["end_date"]
        
        return params
    
    def _build_headers(self, **kwargs: Any) -> dict[str, str]:
        """Build request headers."""
        headers = dict(self.config.request.headers)
        headers = self.config.auth.apply(headers, self.source_settings)
        return headers
    
    def _deduplicate(self, records: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Remove duplicate records."""
        unique_records = []
        
        for record in records:
            hash_input = "".join(
                str(record.get(key, "")) for key in self.config.dedup_keys
            )
            record_hash = hashlib.md5(hash_input.encode()).hexdigest()
            
            if record_hash not in self._seen_hashes:
                self._seen_hashes.add(record_hash)
                unique_records.append(record)
        
        return unique_records
    
    def _validate_record(self, record: dict[str, Any]) -> bool:
        """Validate a record has required fields."""
        for field in self.config.required_fields:
            if field not in record or record[field] is None:
                return False
        return True
    
    def _get_record_hash(self, record: Any) -> str:
        """Get hash for deduplication."""
        if isinstance(record, dict):
            hash_input = "".join(
                str(record.get(key, "")) for key in self.config.dedup_keys
            )
            return hashlib.md5(hash_input.encode()).hexdigest()
        return hashlib.md5(str(record).encode()).hexdigest()
    
    def _is_valid(self, record: Any) -> bool:
        """Check if record is valid."""
        if isinstance(record, dict):
            return self._validate_record(record)
        return True
