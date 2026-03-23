"""
Pydantic Schemas 定义
"""
from pydantic import BaseModel, EmailStr
from typing import Optional, List, Dict, Any
from datetime import datetime


# ============ 通用 ============
class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    username: Optional[str] = None


class BaseResponse(BaseModel):
    code: int = 0
    message: str = "success"
    data: Any = None


# ============ 用户 ============
class UserBase(BaseModel):
    username: str
    real_name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    department: Optional[str] = None
    role: Optional[str] = "user"


class UserCreate(UserBase):
    password: str


class UserUpdate(BaseModel):
    real_name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    department: Optional[str] = None


class UserResponse(UserBase):
    id: int
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class UserLogin(BaseModel):
    username: str
    password: str


# ============ 应用场景 ============
class ApplicationBase(BaseModel):
    title: str
    department: Optional[str] = None
    contact_info: Optional[str] = None
    business_background: Optional[str] = None
    current_pain_points: Optional[str] = None
    expected_value: Optional[str] = None
    cost_estimate: Optional[str] = None
    has_data: bool = False
    has_model: bool = False
    required_resources: Optional[Dict[str, Any]] = None
    workflow_definition_id: Optional[int] = None


class ApplicationCreate(ApplicationBase):
    pass


class ApplicationUpdate(BaseModel):
    title: Optional[str] = None
    department: Optional[str] = None
    contact_info: Optional[str] = None
    business_background: Optional[str] = None
    current_pain_points: Optional[str] = None
    expected_value: Optional[str] = None
    cost_estimate: Optional[str] = None
    has_data: Optional[bool] = None
    has_model: Optional[bool] = None
    required_resources: Optional[Dict[str, Any]] = None
    status: Optional[str] = None


class ApplicationResponse(ApplicationBase):
    id: int
    applicant_id: int
    status: str
    review_comments: Optional[str] = None
    reviewer_id: Optional[int] = None
    approved_at: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ============ 数据集 ============
class DatasetBase(BaseModel):
    name: str
    description: Optional[str] = None
    business_domain: Optional[str] = None
    data_type: Optional[str] = None
    source: Optional[str] = None
    record_count: int = 0
    field_schema: Optional[Dict[str, Any]] = None
    usage_scenarios: Optional[List[str]] = None


class DatasetCreate(DatasetBase):
    workflow_definition_id: Optional[int] = None


class DatasetUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None


class DatasetResponse(DatasetBase):
    id: int
    creator_id: int
    status: str
    workflow_definition_id: Optional[int] = None
    workflow_record_id: Optional[int] = None
    review_comments: Optional[str] = None
    reviewer_id: Optional[int] = None
    approved_at: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ============ 模型 ============
class ModelBase(BaseModel):
    name: str
    description: Optional[str] = None
    model_type: Optional[str] = None
    framework: Optional[str] = None
    version: str = "1.0.0"
    business_scenarios: Optional[List[str]] = None
    performance_metrics: Optional[Dict[str, Any]] = None
    hardware_requirements: Optional[Dict[str, Any]] = None
    has_api: bool = False
    api_docs: Optional[str] = None
    usage_guide: Optional[str] = None


class ModelCreate(ModelBase):
    workflow_definition_id: Optional[int] = None


class ModelUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None


class ModelResponse(ModelBase):
    id: int
    creator_id: int
    source_file_path: Optional[str] = None
    status: str
    workflow_definition_id: Optional[int] = None
    workflow_record_id: Optional[int] = None
    review_comments: Optional[str] = None
    reviewer_id: Optional[int] = None
    approved_at: Optional[datetime] = None
    download_count: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ============ 智能体 ============
class AgentBase(BaseModel):
    name: str
    description: Optional[str] = None
    agent_type: Optional[str] = None
    business_domain: Optional[str] = None
    development_status: Optional[str] = None
    tech_doc: Optional[str] = None
    logic_description: Optional[str] = None
    required_models: Optional[List[int]] = None
    required_datasets: Optional[List[int]] = None
    environment_requirements: Optional[Dict[str, Any]] = None
    api_endpoint: Optional[str] = None


class AgentCreate(AgentBase):
    workflow_definition_id: Optional[int] = None


class AgentUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None


class AgentResponse(AgentBase):
    id: int
    creator_id: int
    status: str
    workflow_definition_id: Optional[int] = None
    workflow_record_id: Optional[int] = None
    review_comments: Optional[str] = None
    reviewer_id: Optional[int] = None
    approved_at: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ============ 应用广场 ============
class AppStoreItemBase(BaseModel):
    name: str
    description: Optional[str] = None
    icon: Optional[str] = None
    category: Optional[str] = None
    business_domain: Optional[str] = None
    developer: Optional[str] = None
    version: str = "1.0.0"
    features: Optional[List[str]] = None
    screenshots: Optional[List[str]] = None
    usage_guide: Optional[str] = None
    sdk_docs: Optional[str] = None


class AppStoreItemCreate(AppStoreItemBase):
    workflow_definition_id: Optional[int] = None


class AppStoreItemResponse(AppStoreItemBase):
    id: int
    usage_count: int
    rating: float
    status: str
    workflow_definition_id: Optional[int] = None
    workflow_record_id: Optional[int] = None
    review_comments: Optional[str] = None
    reviewer_id: Optional[int] = None
    approved_at: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ============ 算力资源 ============
class ComputeResourceBase(BaseModel):
    name: str
    resource_type: Optional[str] = None
    model_name: Optional[str] = None
    memory_size: Optional[int] = None
    total_compute: Optional[float] = None
    location: Optional[str] = None
    owner_department: Optional[str] = None
    support_scenarios: Optional[List[str]] = None


class ComputeResourceCreate(ComputeResourceBase):
    workflow_definition_id: Optional[int] = None


class ComputeResourceResponse(ComputeResourceBase):
    id: int
    used_compute: float
    status: str
    workflow_definition_id: Optional[int] = None
    workflow_record_id: Optional[int] = None
    review_comments: Optional[str] = None
    reviewer_id: Optional[int] = None
    approved_at: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ============ 业务流程 ============
class WorkflowDefinitionBase(BaseModel):
    name: str
    description: Optional[str] = None
    bind_type: str
    bind_subtype: Optional[str] = None
    is_active: bool = True
    version: str = "1.0.0"
    nodes: Optional[List[Dict[str, Any]]] = []
    edges: Optional[List[Dict[str, Any]]] = []


class WorkflowDefinitionCreate(WorkflowDefinitionBase):
    pass


class WorkflowDefinitionResponse(WorkflowDefinitionBase):
    id: int
    created_by: Optional[int] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class WorkflowRecordBase(BaseModel):
    application_id: Optional[int] = None
    record_type: str
    record_id: int
    action: str
    description: Optional[str] = None
    extra_data: Optional[Dict[str, Any]] = None


class WorkflowRecordResponse(WorkflowRecordBase):
    id: int
    actor_id: Optional[int] = None
    created_at: datetime

    class Config:
        from_attributes = True


# ============ 论坛 ============
class ForumPostBase(BaseModel):
    title: str
    content: str
    category: Optional[str] = None
    tags: Optional[List[str]] = None


class ForumPostCreate(ForumPostBase):
    pass


class ForumPostUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    is_pinned: Optional[bool] = None


class ForumPostResponse(ForumPostBase):
    id: int
    author_id: int
    view_count: int
    like_count: int
    comment_count: int
    is_pinned: bool
    status: str
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ============ 申请记录 ============
class ApplicationRequestBase(BaseModel):
    request_type: str
    resource_id: int
    resource_name: str
    purpose: Optional[str] = None
    expected_duration: Optional[int] = None
    expected_frequency: Optional[str] = None
    related_application: Optional[str] = None


class ApplicationRequestCreate(ApplicationRequestBase):
    pass


class ApplicationRequestResponse(ApplicationRequestBase):
    id: int
    applicant_id: int
    applicant_department: Optional[str] = None
    status: str
    reviewer_id: Optional[int] = None
    review_comments: Optional[str] = None
    approved_at: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ============ 仪表盘统计 ============
class DashboardStats(BaseModel):
    model_count: int = 0
    application_count: int = 0
    dataset_count: int = 0
    agent_count: int = 0
    compute_total: float = 0.0
    compute_used: float = 0.0
    user_count: int = 0


class ChartData(BaseModel):
    labels: List[str]
    values: List[Any]


# ============ 系统配置 - 角色管理 ============
class RoleBase(BaseModel):
    name: str
    code: str
    description: Optional[str] = None
    permissions: Optional[List[str]] = []
    is_system: bool = False
    is_active: bool = True


class RoleCreate(RoleBase):
    pass


class RoleUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    permissions: Optional[List[str]] = None
    is_active: Optional[bool] = None


class RoleResponse(RoleBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class UserRoleAssign(BaseModel):
    role_id: int
    expires_at: Optional[str] = None


# ============ 站内通知 ============
class NotificationBase(BaseModel):
    title: str
    content: str
    type: Optional[str] = "system"
    related_type: Optional[str] = None
    related_id: Optional[int] = None


class NotificationCreate(NotificationBase):
    user_id: int


class NotificationUpdate(BaseModel):
    is_read: Optional[bool] = None


class NotificationResponse(NotificationBase):
    id: int
    user_id: int
    is_read: bool
    read_at: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class NotificationListResponse(BaseModel):
    items: List[NotificationResponse]
    total: int
    unread_count: int


# ============ 论坛评论 ============
class ForumCommentBase(BaseModel):
    content: str
    parent_id: Optional[int] = None


class ForumCommentCreate(BaseModel):
    content: str
    parent_id: Optional[int] = None


class ForumCommentResponse(ForumCommentBase):
    id: int
    post_id: int
    author_id: int
    like_count: int
    is_deleted: bool
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ============ 部门管理 ============
class DepartmentBase(BaseModel):
    name: str
    code: str
    description: Optional[str] = None
    parent_id: Optional[int] = None
    manager_id: Optional[int] = None
    is_active: bool = True


class DepartmentCreate(DepartmentBase):
    pass


class DepartmentUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    parent_id: Optional[int] = None
    manager_id: Optional[int] = None
    is_active: Optional[bool] = None


class DepartmentResponse(DepartmentBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    parent: Optional["DepartmentResponse"] = None
    children: Optional[list["DepartmentResponse"]] = []
    manager: Optional[UserResponse] = None
    member_count: int = 0

    class Config:
        from_attributes = True
