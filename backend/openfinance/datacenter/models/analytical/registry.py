"""
ADS Model Registry - ADS 模型注册中心。

支持:
- 动态注册 ADS 模型
- YAML 配置驱动模型生成
- 自动创建 Repository
- ORM ↔ ADS 字段映射管理
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

import yaml

from pydantic import BaseModel, Field, create_model

from openfinance.datacenter.models.analytical.base import (
    ADSModel,
    ADSModelWithCode,
    ADSModelWithDate,
    ADSModelWithReportDate,
    DataCategory,
    DataQuality,
)

logger = logging.getLogger(__name__)


@dataclass
class ADSFieldDefinition:
    """ADS 字段定义。"""
    name: str
    type: str
    required: bool = False
    default: Any = None
    description: str = ""
    orm_field: str | None = None
    alias: str | None = None
    computed: bool = False
    computed_expr: str | None = None


@dataclass
class ADSModelDefinition:
    """ADS 模型定义。"""
    model_id: str
    category: DataCategory
    description: str = ""
    base_model: str = "ADSModel"
    fields: list[ADSFieldDefinition] = field(default_factory=list)
    orm_model: str | None = None
    table_name: str | None = None
    primary_key: list[str] = field(default_factory=list)
    unique_keys: list[list[str]] = field(default_factory=list)
    field_mappings: dict[str, str] = field(default_factory=dict)
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "model_id": self.model_id,
            "category": self.category.value,
            "description": self.description,
            "base_model": self.base_model,
            "orm_model": self.orm_model,
            "table_name": self.table_name,
            "primary_key": self.primary_key,
            "fields": [
                {
                    "name": f.name,
                    "type": f.type,
                    "required": f.required,
                    "description": f.description,
                    "orm_field": f.orm_field,
                }
                for f in self.fields
            ],
            "field_mappings": self.field_mappings,
        }


class ADSModelRegistry:
    """
    ADS 模型注册中心。
    
    功能:
    - 注册 ADS 模型定义
    - 从 YAML 配置加载模型
    - 动态生成 Pydantic 模型类
    - 管理 ORM ↔ ADS 字段映射
    - 自动创建 Repository
    
    使用示例:
        registry = ADSModelRegistry.get_instance()
        
        # 从 YAML 加载
        registry.load_from_yaml("config/data_types/market_kline.yaml")
        
        # 获取模型
        model_class = registry.get_model("market_kline")
        repository = registry.get_repository("market_kline")
    """
    
    _instance = None
    
    def __new__(cls) -> "ADSModelRegistry":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self) -> None:
        if self._initialized:
            return
        
        self._model_definitions: dict[str, ADSModelDefinition] = {}
        self._model_classes: dict[str, type[ADSModel]] = {}
        self._repositories: dict[str, Any] = {}
        self._orm_mappings: dict[str, dict[str, str]] = {}
        
        self._type_mapping = {
            "string": str,
            "int": int,
            "float": float,
            "bool": bool,
            "date": datetime,
            "datetime": datetime,
            "list": list,
            "dict": dict,
        }
        
        self._base_models = {
            "ADSModel": ADSModel,
            "ADSModelWithCode": ADSModelWithCode,
            "ADSModelWithDate": ADSModelWithDate,
            "ADSModelWithReportDate": ADSModelWithReportDate,
        }
        
        self._initialized = True
        logger.info("ADSModelRegistry initialized")
    
    @classmethod
    def get_instance(cls) -> "ADSModelRegistry":
        return cls()
    
    @classmethod
    def reset(cls) -> None:
        cls._instance = None
    
    def register(
        self,
        model_id: str,
        category: DataCategory,
        model_class: type[ADSModel] | None = None,
        orm_model: type | None = None,
        field_mappings: dict[str, str] | None = None,
        description: str = "",
    ) -> ADSModelDefinition:
        """
        注册 ADS 模型。
        
        Args:
            model_id: 模型唯一标识
            category: 数据分类
            model_class: ADS 模型类（可选，不提供则动态生成）
            orm_model: 对应的 ORM 模型类
            field_mappings: ORM → ADS 字段映射
            description: 模型描述
        
        Returns:
            ADSModelDefinition 模型定义
        """
        if model_class:
            self._model_classes[model_id] = model_class
        
        definition = ADSModelDefinition(
            model_id=model_id,
            category=category,
            description=description,
            orm_model=orm_model.__name__ if orm_model else None,
            field_mappings=field_mappings or {},
        )
        
        self._model_definitions[model_id] = definition
        
        if orm_model:
            self._orm_mappings[model_id] = field_mappings or {}
        
        logger.info(f"Registered ADS model: {model_id}")
        return definition
    
    def load_from_yaml(self, config_path: str) -> ADSModelDefinition | None:
        """
        从 YAML 配置文件加载模型定义。
        
        YAML 格式:
        ```yaml
        model_id: market_kline
        category: market
        description: 股票K线数据
        base_model: ADSModelWithCode
        orm_model: StockDailyQuoteModel
        table_name: stock_daily_quote
        primary_key: [code, trade_date]
        fields:
          - name: code
            type: string
            required: true
            description: 股票代码
          - name: trade_date
            type: date
            required: true
            orm_field: trade_date
          - name: close
            type: float
            orm_field: close
        field_mappings:
          collected_at: updated_at
        ```
        """
        path = Path(config_path)
        if not path.exists():
            logger.error(f"Config file not found: {config_path}")
            return None
        
        with open(path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
        
        return self.load_from_dict(config)
    
    def load_from_dict(self, config: dict[str, Any]) -> ADSModelDefinition:
        """从字典配置加载模型定义。"""
        model_id = config["model_id"]
        category = DataCategory(config.get("category", "market"))
        
        fields = []
        field_mappings = dict(config.get("field_mappings", {}))
        
        for f in config.get("fields", []):
            field_def = ADSFieldDefinition(
                name=f["name"],
                type=f.get("type", "string"),
                required=f.get("required", False),
                default=f.get("default"),
                description=f.get("description", ""),
                orm_field=f.get("orm_field"),
                alias=f.get("alias"),
                computed=f.get("computed", False),
                computed_expr=f.get("computed_expr"),
            )
            fields.append(field_def)
            
            if field_def.alias:
                field_mappings[field_def.name] = field_def.alias
        
        definition = ADSModelDefinition(
            model_id=model_id,
            category=category,
            description=config.get("description", ""),
            base_model=config.get("base_model", "ADSModel"),
            fields=fields,
            orm_model=config.get("orm_model"),
            table_name=config.get("table_name"),
            primary_key=config.get("primary_key", []),
            unique_keys=config.get("unique_keys", []),
            field_mappings=field_mappings,
        )
        
        self._model_definitions[model_id] = definition
        self._orm_mappings[model_id] = definition.field_mappings
        
        model_class = self._create_model_class(definition)
        if model_class:
            self._model_classes[model_id] = model_class
        
        logger.info(f"Loaded ADS model from config: {model_id}")
        return definition
    
    def _create_model_class(self, definition: ADSModelDefinition) -> type[ADSModel] | None:
        """动态创建 Pydantic 模型类。"""
        base_class = self._base_models.get(
            definition.base_model, ADSModel
        )
        
        base_fields = set()
        for base in base_class.__mro__:
            if hasattr(base, 'model_fields'):
                base_fields.update(base.model_fields.keys())
        
        fields = {}
        for f in definition.fields:
            if f.computed:
                continue
            if f.name in base_fields:
                continue
            
            field_type = self._type_mapping.get(f.type, str)
            if not f.required:
                field_type = field_type | None
            
            field_kwargs = {}
            if f.description:
                field_kwargs["description"] = f.description
            if f.alias:
                field_kwargs["alias"] = f.alias
            if f.default is not None:
                field_kwargs["default"] = f.default
            elif not f.required:
                field_kwargs["default"] = None
            
            fields[f.name] = (field_type, Field(**field_kwargs) if field_kwargs else field_type)
        
        try:
            model_class = create_model(
                f"{definition.model_id}_model",
                __base__=base_class,
                **fields,
            )
            return model_class
        except Exception as e:
            logger.error(f"Failed to create model class for {definition.model_id}: {e}")
            return None
    
    def load_all_from_yaml(self, config_path: str) -> list[ADSModelDefinition]:
        """
        从 YAML 配置文件批量加载所有模型定义。
        
        YAML 格式:
        ```yaml
        data_types:
          - model_id: kline
            category: market
            description: 股票K线数据
            orm_model: StockDailyQuoteModel
            fields:
              - name: code
                type: string
                required: true
          - model_id: factor
            category: quant
            fields:
              - name: factor_value
                type: float
                alias: value
        ```
        
        Args:
            config_path: YAML 配置文件路径
            
        Returns:
            加载的模型定义列表
        """
        path = Path(config_path)
        if not path.exists():
            logger.error(f"Config file not found: {config_path}")
            return []
        
        with open(path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
        
        definitions = []
        data_types = config.get("data_types", [])
        
        for model_config in data_types:
            try:
                definition = self.load_from_dict(model_config)
                definitions.append(definition)
            except Exception as e:
                logger.error(f"Failed to load model {model_config.get('model_id', 'unknown')}: {e}")
        
        logger.info(f"Loaded {len(definitions)} models from {config_path}")
        return definitions
    
    def load_from_yaml_dir(self, dir_path: str) -> list[ADSModelDefinition]:
        """
        从目录中的所有 YAML 文件加载模型定义。
        
        Args:
            dir_path: YAML 配置文件目录
            
        Returns:
            加载的模型定义列表
        """
        dir_path = Path(dir_path)
        if not dir_path.exists():
            logger.error(f"Config directory not found: {dir_path}")
            return []
        
        definitions = []
        for yaml_file in dir_path.glob("**/*.yaml"):
            try:
                file_definitions = self.load_all_from_yaml(str(yaml_file))
                definitions.extend(file_definitions)
            except Exception as e:
                logger.error(f"Failed to load from {yaml_file}: {e}")
        
        return definitions
    
    def get_model(self, model_id: str) -> type[ADSModel] | None:
        """获取 ADS 模型类。"""
        return self._model_classes.get(model_id)
    
    def get_definition(self, model_id: str) -> ADSModelDefinition | None:
        """获取模型定义。"""
        return self._model_definitions.get(model_id)
    
    def get_field_mappings(self, model_id: str) -> dict[str, str]:
        """获取 ORM → ADS 字段映射。"""
        return self._orm_mappings.get(model_id, {})
    
    def get_model_ids(self, category: DataCategory | None = None) -> list[str]:
        """获取模型 ID 列表。"""
        if category:
            return [
                mid for mid, defn in self._model_definitions.items()
                if defn.category == category
            ]
        return list(self._model_definitions.keys())
    
    def list_definitions(self, category: DataCategory | None = None) -> list[ADSModelDefinition]:
        """列出模型定义。"""
        if category:
            return [
                defn for defn in self._model_definitions.values()
                if defn.category == category
            ]
        return list(self._model_definitions.values())
    
    def get_stats(self) -> dict[str, Any]:
        """获取注册中心统计信息。"""
        return {
            "total_models": len(self._model_definitions),
            "categories": {
                cat.value: len([
                    m for m in self._model_definitions.values()
                    if m.category == cat
                ])
                for cat in DataCategory
            },
            "models_with_orm": sum(
                1 for m in self._model_definitions.values()
                if m.orm_model is not None
            ),
            "generated_models": len(self._model_classes),
        }
    
    def create_repository(
        self,
        model_id: str,
        orm_model_class: type | None = None,
        ads_model_class: type[ADSModel] | None = None,
    ) -> Any | None:
        """
        动态创建 Repository 实例。
        
        Args:
            model_id: 模型 ID
            orm_model_class: ORM 模型类（可选，从注册中心获取）
            ads_model_class: ADS 模型类（可选，从注册中心获取）
        
        Returns:
            GenericADSRepository 实例或 None
        """
        from openfinance.datacenter.models.analytical.repository import GenericADSRepository
        
        definition = self.get_definition(model_id)
        if not definition:
            logger.warning(f"Model definition not found: {model_id}")
            return None
        
        ads_model = ads_model_class or self.get_model(model_id)
        if not ads_model:
            logger.warning(f"ADS model not found: {model_id}")
            return None
        
        if orm_model_class is None and definition.orm_model:
            orm_model_class = self._get_orm_model(definition.orm_model)
        
        if not orm_model_class:
            logger.warning(f"ORM model not found for: {model_id}")
            return None
        
        class DynamicRepository(GenericADSRepository):
            pass
        
        DynamicRepository.__name__ = f"{model_id}_repository"
        DynamicRepository.orm_model_class = orm_model_class
        DynamicRepository.ads_model_class = ads_model
        
        return DynamicRepository()
    
    def _get_orm_model(self, model_name: str) -> type | None:
        """根据名称获取 ORM 模型类。"""
        from openfinance.datacenter.models import orm
        
        return getattr(orm, model_name, None)
    
    def get_repository(self, model_id: str) -> Any | None:
        """获取或创建 Repository 实例。"""
        if model_id in self._repositories:
            return self._repositories[model_id]
        
        repository = self.create_repository(model_id)
        if repository:
            self._repositories[model_id] = repository
        
        return repository
    
    def register_repository(self, model_id: str, repository: Any) -> None:
        """注册自定义 Repository。"""
        self._repositories[model_id] = repository
        logger.info(f"Registered repository for: {model_id}")


def register_ads_model(
    model_id: str,
    category: DataCategory,
    orm_model: type | None = None,
    field_mappings: dict[str, str] | None = None,
) -> Callable[[type[ADSModel]], type[ADSModel]]:
    """
    装饰器：注册 ADS 模型。
    
    使用示例:
        @register_ads_model(
            model_id="market_kline",
            category=DataCategory.MARKET,
            orm_model=StockDailyQuoteModel,
            field_mappings={"collected_at": "updated_at"},
        )
        class ADSKLineModel(ADSModelWithCode, ADSModelWithDate):
            open: float | None
            high: float | None
            close: float | None
    """
    def decorator(cls: type[ADSModel]) -> type[ADSModel]:
        registry = ADSModelRegistry.get_instance()
        registry.register(
            model_id=model_id,
            category=category,
            model_class=cls,
            orm_model=orm_model,
            field_mappings=field_mappings,
        )
        return cls
    
    return decorator
