from enum import Enum
from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field


class QueueType(str, Enum):
    FIXED = "fixed"
    ELASTIC = "elastic"


class QueueState(str, Enum):
    RUNNING = "RUNNING"
    STOPPED = "STOPPED"
    DRAINING = "DRAINING"


class ResourceAllocation(BaseModel):
    memory_mb: int = 0
    vcores: int = 0


class PartitionResourceConfig(BaseModel):
    partition_name: str = "DEFAULT"
    capacity: float = Field(..., description="Гарантированная емкость (% или абсолютное значение)")
    max_capacity: float = Field(..., description="Максимальная емкость (% или абсолютное значение)")
    is_elastic: bool = Field(False, description="Эластичная ли очередь (max_capacity > capacity)")
    elasticity_ratio: float = Field(1.0, description="Коэффициент эластичности (max_capacity / capacity)")
    absolute_resources: Optional[ResourceAllocation] = None
    absolute_max_resources: Optional[ResourceAllocation] = None


class QueueNode(BaseModel):
    name: str
    path: str
    parent_path: Optional[str] = None
    is_leaf: bool = True
    state: QueueState = QueueState.RUNNING
    partitions: Dict[str, PartitionResourceConfig] = Field(default_factory=dict)
    
    # Текущие метрики использования из YARN RM
    current_used_resources: ResourceAllocation = Field(default_factory=ResourceAllocation)
    allocated_resources: ResourceAllocation = Field(default_factory=ResourceAllocation)
    current_used_percent: float = 0.0
    num_applications: int = 0
    num_active_applications: int = 0
    num_pending_applications: int = 0
    
    children: List["QueueNode"] = Field(default_factory=list)


class ClusterMetrics(BaseModel):
    total_memory_mb: int
    total_vcores: int
    allocated_memory_mb: int
    allocated_vcores: int
    available_memory_mb: int
    available_vcores: int
    active_nodes: int
    unhealthy_nodes: int
    total_containers: int
    running_apps: int
    partitions: List[str]


class BranchBalance(BaseModel):
    parent_path: str
    partition: str
    total_children_capacity: float
    unallocated_capacity: float
    is_balanced: bool
    status: str  # "ok", "underallocated", "overallocated"
    message: str


class QueueTreeResponse(BaseModel):
    cluster_id: str
    cluster_name: str
    resource_mode: str
    default_partition: str
    partitions: List[str]
    root_queue: QueueNode
    cluster_metrics: ClusterMetrics
    balances: List[BranchBalance]


# Модели для черновиков (Draft), Diff и генерации XML
class QueueDraftItem(BaseModel):
    path: str
    name: str
    parent_path: Optional[str] = None
    action: str = "modify"  # modify | create | delete
    is_leaf: bool = True
    state: QueueState = QueueState.RUNNING
    partitions: Dict[str, PartitionResourceConfig]


class DraftValidateRequest(BaseModel):
    cluster_id: str
    selected_partition: str = "DEFAULT"
    queues: List[QueueDraftItem]


class DraftValidateResponse(BaseModel):
    is_valid: bool
    balances: List[BranchBalance]
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)


class DiffItem(BaseModel):
    path: str
    name: str
    parent_path: Optional[str] = None
    partition: str
    action: str  # created, modified, deleted, unchanged
    
    live_capacity: Optional[float] = None
    draft_capacity: Optional[float] = None
    delta_capacity: Optional[float] = None
    
    live_max_capacity: Optional[float] = None
    draft_max_capacity: Optional[float] = None
    delta_max_capacity: Optional[float] = None
    
    live_type: Optional[QueueType] = None
    draft_type: Optional[QueueType] = None
    
    live_state: Optional[QueueState] = None
    draft_state: Optional[QueueState] = None


class DraftDiffResponse(BaseModel):
    cluster_id: str
    has_changes: bool
    diffs: List[DiffItem]


class GenerateXmlRequest(BaseModel):
    cluster_id: str
    queues: List[QueueDraftItem]
    proposal_comment: Optional[str] = None


class GenerateXmlResponse(BaseModel):
    cluster_id: str
    filename: str
    xml_content: str
    applied_by: str
    generated_at: str
    instructions: str
