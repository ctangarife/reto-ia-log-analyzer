"""
Esquemas para el sistema multi-proveedor LLM
"""
from pydantic import BaseModel, Field
from typing import List, Optional, Literal, Dict
from enum import Enum


class LLMProvider(str, Enum):
    """Proveedores LLM disponibles"""
    ollama = "ollama"
    zai = "zai"
    minimax = "minimax"


class LLMModelRole(str, Enum):
    """Roles de modelos LLM"""
    default = "default"      # Modelo principal
    fallback = "fallback"    # Modelo alternativo
    evaluator = "evaluator"  # Modelo para evaluación


class LLMDynamicCredentials(BaseModel):
    """Credenciales dinámicas por proveedor"""
    zai: Optional[Dict[str, str]] = Field(default=None, description="Credenciales Z.ai: {apiKey, apiEndpoint}")
    minimax: Optional[Dict[str, str]] = Field(default=None, description="Credenciales MiniMax: {apiKey, apiEndpoint}")
    ollama: Optional[Dict[str, str]] = Field(default=None, description="Credenciales Ollama Cloud: {apiKey, apiEndpoint}")

    defaultProvider: LLMProvider = Field(default=LLMProvider.ollama)
    defaultModel: str = Field(default="qwen2.5:3b")


class LLMModelInfo(BaseModel):
    """Información de un modelo LLM"""
    id: str
    provider: LLMProvider
    name: str
    context_size: Optional[int] = None
    description: Optional[str] = None


class LLMModelList(BaseModel):
    """Lista de modelos disponibles"""
    models: List[LLMModelInfo]
    default_provider: LLMProvider
    default_model: str


class LLMConfigRequest(BaseModel):
    """Request para configurar el modelo LLM"""
    provider: LLMProvider
    model: str
    credentials: Optional[LLMDynamicCredentials] = None
    setAsDefault: Optional[bool] = True  # Por defecto True para compatibilidad, pero la UI puede controlarlo


class LLMConfigResponse(BaseModel):
    """Respuesta con la configuración actual"""
    provider: LLMProvider
    model: str
    is_available: bool
    available_models: List[str]


class WorkspaceLLMModelConfig(BaseModel):
    """Configuración completa de un modelo LLM"""
    provider: LLMProvider
    model: str
    role: LLMModelRole
    has_credentials: bool
    is_available: Optional[bool] = None
    priority: Optional[int] = None  # Para orden de fallback (1, 2, 3...)


class LLMModelSelectionConfig(BaseModel):
    """Configuración de selección de modelos del workspace"""
    default_model: Optional[WorkspaceLLMModelConfig] = None
    fallback_models: List[WorkspaceLLMModelConfig] = []
    evaluator_models: List[WorkspaceLLMModelConfig] = []


class LLMConfigRequestWithRole(BaseModel):
    """Request para configurar modelo con rol específico"""
    provider: LLMProvider
    model: str
    role: LLMModelRole = Field(default=LLMModelRole.default)
    priority: Optional[int] = Field(None, description="Prioridad para modelos fallback (menor = mayor prioridad)")
    credentials: Optional[LLMDynamicCredentials] = None


class LLMModelConfigBatch(BaseModel):
    """Configuración de un modelo para batch update (sin role porque ya está implícito)"""
    provider: LLMProvider
    model: str
    credentials: Optional[LLMDynamicCredentials] = None


class LLMBatchConfigRequest(BaseModel):
    """Request para configurar múltiples modelos de una vez"""
    default: Optional[LLMModelConfigBatch] = None
    fallback: List[LLMModelConfigBatch] = []
    evaluators: List[LLMModelConfigBatch] = []
