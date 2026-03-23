"""
数据库模型定义
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, Float, Boolean, ForeignKey, Enum, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum

from app.core.database import Base


# ============ 用户相关 ============
class User(Base):
    """用户表"""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    real_name = Column(String(100))
    email = Column(String(100))
    phone = Column(String(20))
    department = Column(String(100))  # 所属部门（文本字段，兼容旧数据）
    department_id = Column(Integer, ForeignKey("departments.id"), nullable=True)  # 所属部门 ID
    role = Column(String(20), default="user")  # user, reviewer, admin
    is_department_manager = Column(Boolean, default=False)  # 是否部门负责人
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # 关联
    applications = relationship("Application", back_populates="applicant", foreign_keys="Application.applicant_id")
    created_datasets = relationship("Dataset", foreign_keys="Dataset.creator_id", back_populates="creator")
    created_models = relationship("Model", foreign_keys="Model.creator_id", back_populates="creator")
    created_agents = relationship("Agent", foreign_keys="Agent.creator_id", back_populates="creator")
    assigned_roles = relationship("UserRole", foreign_keys="UserRole.user_id", back_populates="user")
    department_rel = relationship("Department", back_populates="members", foreign_keys=[department_id])


# ============ 应用场景 ============
class ApplicationStatus(enum.Enum):
    DRAFT = "draft"  # 草稿
    SUBMITTED = "submitted"  # 已提交
    UNDER_REVIEW = "under_review"  # 审核中
    APPROVED = "approved"  # 已通过
    REJECTED = "rejected"  # 已拒绝
    IN_PROGRESS = "in_progress"  # 进行中
    COMPLETED = "completed"  # 已完成


class Application(Base):
    """应用场景申报表"""
    __tablename__ = "applications"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False)  # 应用名称
    applicant_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    department = Column(String(100))  # 申报部门
    contact_info = Column(String(100))  # 联系方式
    business_background = Column(Text)  # 业务背景
    current_pain_points = Column(Text)  # 当前痛点
    expected_value = Column(Text)  # 预期价值
    cost_estimate = Column(Text)  # 成本估算
    has_data = Column(Boolean, default=False)  # 是否具备数据
    has_model = Column(Boolean, default=False)  # 是否具备模型
    required_resources = Column(JSON)  # 所需资源
    workflow_definition_id = Column(Integer, ForeignKey("workflow_definitions.id"))  # 绑定的工作流定义
    status = Column(String(20), default="draft")
    review_comments = Column(Text)  # 审核意见
    reviewer_id = Column(Integer, ForeignKey("users.id"))  # 审核人
    approved_at = Column(DateTime(timezone=True))  # 审批时间
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    applicant = relationship("User", back_populates="applications", foreign_keys=[applicant_id])


# ============ 数据集 ============
class DatasetType(enum.Enum):
    STRUCTURED = "structured"  # 结构化数据
    UNSTRUCTURED = "unstructured"  # 非结构化数据


class DatasetSource(enum.Enum):
    INTERNAL = "internal"  # 内部系统
    EXTERNAL = "external"  # 外部采购


class Dataset(Base):
    """数据集"""
    __tablename__ = "datasets"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    description = Column(Text)
    creator_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    business_domain = Column(String(50))  # 业务领域：财务、合同、水电等
    data_type = Column(String(20))  # structured/unstructured
    source = Column(String(20))  # internal/external
    status = Column(String(20), default="pending")  # pending, under_review, approved, rejected, archived
    record_count = Column(Integer, default=0)  # 数据量
    field_schema = Column(JSON)  # 字段说明
    usage_scenarios = Column(JSON)  # 使用场景
    workflow_definition_id = Column(Integer, ForeignKey("workflow_definitions.id"), nullable=True)  # 绑定的工作流
    workflow_record_id = Column(Integer, ForeignKey("workflow_records.id"), nullable=True)  # 当前工作流记录
    review_comments = Column(Text)  # 审核意见
    reviewer_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # 审核人
    approved_at = Column(DateTime(timezone=True), nullable=True)  # 审批时间
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    creator = relationship("User", foreign_keys=[creator_id], back_populates="created_datasets")
    reviewer = relationship("User", foreign_keys=[reviewer_id])


# ============ 模型 ============
class Model(Base):
    """AI 模型"""
    __tablename__ = "models"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    description = Column(Text)
    creator_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    model_type = Column(String(50))  # 模型类型：NLP, CV, ASR, TTS 等
    framework = Column(String(50))  # 框架：PyTorch, TensorFlow 等
    version = Column(String(20), default="1.0.0")
    business_scenarios = Column(JSON)  # 适用场景
    performance_metrics = Column(JSON)  # 性能指标
    hardware_requirements = Column(JSON)  # 硬件要求
    has_api = Column(Boolean, default=False)  # 是否具备 API
    api_docs = Column(Text)  # API 文档
    usage_guide = Column(Text)  # 使用说明
    source_file_path = Column(String(500))  # 源文件路径
    status = Column(String(20), default="pending")  # pending, under_review, approved, rejected, available
    download_count = Column(Integer, default=0)
    workflow_definition_id = Column(Integer, ForeignKey("workflow_definitions.id"), nullable=True)  # 绑定的工作流
    workflow_record_id = Column(Integer, ForeignKey("workflow_records.id"), nullable=True)  # 当前工作流记录
    review_comments = Column(Text)  # 审核意见
    reviewer_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # 审核人
    approved_at = Column(DateTime(timezone=True), nullable=True)  # 审批时间
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    creator = relationship("User", foreign_keys=[creator_id], back_populates="created_models")
    reviewer = relationship("User", foreign_keys=[reviewer_id])


# ============ 智能体 ============
class Agent(Base):
    """AI 智能体/MCP"""
    __tablename__ = "agents"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    description = Column(Text)
    creator_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    agent_type = Column(String(50))  # MCP, AI+ 业务场景等
    business_domain = Column(String(50))  # 业务领域
    development_status = Column(String(20))  # planning, developing, testing, released
    tech_doc = Column(Text)  # 技术文档
    logic_description = Column(Text)  # 逻辑说明
    required_models = Column(JSON)  # 依赖模型
    required_datasets = Column(JSON)  # 依赖数据集
    environment_requirements = Column(JSON)  # 运行环境要求
    api_endpoint = Column(String(500))  # 接口地址
    status = Column(String(20), default="pending")  # pending, under_review, approved, rejected, available
    workflow_definition_id = Column(Integer, ForeignKey("workflow_definitions.id"), nullable=True)  # 绑定的工作流
    workflow_record_id = Column(Integer, ForeignKey("workflow_records.id"), nullable=True)  # 当前工作流记录
    review_comments = Column(Text)  # 审核意见
    reviewer_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # 审核人
    approved_at = Column(DateTime(timezone=True), nullable=True)  # 审批时间
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    creator = relationship("User", foreign_keys=[creator_id], back_populates="created_agents")
    reviewer = relationship("User", foreign_keys=[reviewer_id])


# ============ 应用广场 ============
class AppStoreItem(Base):
    """应用广场项目"""
    __tablename__ = "app_store"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    description = Column(Text)
    icon = Column(String(500))  # 图标
    category = Column(String(50))  # 分类：通用应用，定制化应用
    business_domain = Column(String(50))  # 业务领域
    developer = Column(String(100))  # 开发者
    version = Column(String(20))
    usage_count = Column(Integer, default=0)
    rating = Column(Float, default=0.0)  # 评分
    features = Column(JSON)  # 功能特性
    screenshots = Column(JSON)  # 截图
    usage_guide = Column(Text)  # 使用指南
    sdk_docs = Column(Text)  # SDK 文档
    status = Column(String(20), default="pending")  # pending, under_review, approved, rejected, published
    workflow_definition_id = Column(Integer, ForeignKey("workflow_definitions.id"), nullable=True)  # 绑定的工作流
    workflow_record_id = Column(Integer, ForeignKey("workflow_records.id"), nullable=True)  # 当前工作流记录
    review_comments = Column(Text)  # 审核意见
    reviewer_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # 审核人
    approved_at = Column(DateTime(timezone=True), nullable=True)  # 审批时间
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    reviewer = relationship("User", foreign_keys=[reviewer_id])


# ============ 算力资源 ============
class ComputeResource(Base):
    """算力资源"""
    __tablename__ = "compute_resources"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    resource_type = Column(String(50))  # GPU, CPU, TPU
    model_name = Column(String(100))  # 型号：A100, H100 等
    memory_size = Column(Integer)  # 显存/内存 (GB)
    total_compute = Column(Float)  # 总算力 (TFLOPS)
    used_compute = Column(Float, default=0)  # 已用算力
    status = Column(String(20), default="pending")  # pending, under_review, approved, rejected, available, in_use, maintenance
    location = Column(String(100))  # 位置
    owner_department = Column(String(100))  # 所属部门
    support_scenarios = Column(JSON)  # 支持场景：训练，推理等
    workflow_definition_id = Column(Integer, ForeignKey("workflow_definitions.id"), nullable=True)  # 绑定的工作流
    workflow_record_id = Column(Integer, ForeignKey("workflow_records.id"), nullable=True)  # 当前工作流记录
    review_comments = Column(Text)  # 审核意见
    reviewer_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # 审核人
    approved_at = Column(DateTime(timezone=True), nullable=True)  # 审批时间
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    reviewer = relationship("User", foreign_keys=[reviewer_id])


# ============ 业务流程 ============
class WorkflowDefinition(Base):
    """工作流定义 - 可自定义的审核流程"""
    __tablename__ = "workflow_definitions"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)  # 工作流名称
    description = Column(Text)  # 工作流描述
    bind_type = Column(String(50))  # 绑定类型：application, dataset, model, agent, compute
    bind_subtype = Column(String(50))  # 绑定子类型：如 application 的 new/review 等
    is_active = Column(Boolean, default=True)  # 是否启用
    version = Column(String(20), default="1.0.0")  # 版本号
    nodes = Column(JSON)  # 节点配置 [{id, type, name, x, y, config}, ...]
    edges = Column(JSON)  # 连接线配置 [{source, target}, ...]
    created_by = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class WorkflowNode:
    """工作流节点类型定义"""
    START = "start"  # 开始节点
    END = "end"  # 结束节点
    SUBMIT = "submit"  # 提交节点
    REVIEW = "review"  # 审核节点
    APPROVE = "approve"  # 审批节点
    NOTIFY = "notify"  # 通知节点
    CONDITION = "condition"  # 条件分支
    PARALLEL = "parallel"  # 并行节点


class WorkflowRecord(Base):
    """业务流程记录"""
    __tablename__ = "workflow_records"

    id = Column(Integer, primary_key=True, index=True)
    application_id = Column(Integer, ForeignKey("applications.id"))
    workflow_definition_id = Column(Integer, ForeignKey("workflow_definitions.id"))  # 关联的工作流定义
    current_node_id = Column(String(50))  # 当前节点 ID
    record_type = Column(String(50))  # application, dataset, model, agent, compute
    record_id = Column(Integer)  # 对应记录的 ID
    action = Column(String(50))  # apply, review, approve, use, optimize, release
    actor_id = Column(Integer, ForeignKey("users.id"))  # 操作人
    description = Column(Text)
    extra_data = Column(JSON)  # 元数据
    node_status = Column(String(20), default="pending")  # pending, completed, skipped
    created_at = Column(DateTime(timezone=True), server_default=func.now())


# ============ 论坛 ============
class ForumPost(Base):
    """论坛帖子"""
    __tablename__ = "forum_posts"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False)
    content = Column(Text, nullable=False)
    author_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    category = Column(String(50))  # 分类：技术分享，案例分析，问答等
    tags = Column(JSON)  # 标签
    view_count = Column(Integer, default=0)
    like_count = Column(Integer, default=0)
    comment_count = Column(Integer, default=0)
    is_pinned = Column(Boolean, default=False)  # 是否置顶
    status = Column(String(20), default="published")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class ForumComment(Base):
    """论坛评论"""
    __tablename__ = "forum_comments"

    id = Column(Integer, primary_key=True, index=True)
    post_id = Column(Integer, ForeignKey("forum_posts.id"), nullable=False)
    author_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    parent_id = Column(Integer, ForeignKey("forum_comments.id"), nullable=True)  # 回复的评论 ID
    content = Column(Text, nullable=False)
    like_count = Column(Integer, default=0)
    is_deleted = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # 关联
    post = relationship("ForumPost", backref="comments")
    author = relationship("User", foreign_keys=[author_id])
    parent = relationship("ForumComment", remote_side=[id], backref="replies")


# ============ 申请记录 ============
class ApplicationRequest(Base):
    """资源申请记录（数据/模型/智能体/算力）"""
    __tablename__ = "application_requests"

    id = Column(Integer, primary_key=True, index=True)
    request_type = Column(String(50), nullable=False)  # dataset, model, agent, compute
    resource_id = Column(Integer, nullable=False)  # 资源 ID
    resource_name = Column(String(200))  # 资源名称
    applicant_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    applicant_department = Column(String(100))
    purpose = Column(Text)  # 申请用途
    expected_duration = Column(Integer)  # 预计使用天数
    expected_frequency = Column(String(100))  # 预计调用频率
    related_application = Column(String(200))  # 关联应用场景
    workflow_definition_id = Column(Integer, ForeignKey("workflow_definitions.id"))  # 绑定的工作流定义
    workflow_record_id = Column(Integer, ForeignKey("workflow_records.id"))  # 关联的工作流记录
    status = Column(String(20), default="pending")  # pending, approved, rejected, under_review
    reviewer_id = Column(Integer, ForeignKey("users.id"))
    review_comments = Column(Text)
    approved_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


# ============ 系统配置 - 角色管理 ============
class Role(Base):
    """角色表"""
    __tablename__ = "roles"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), unique=True, nullable=False)  # 角色名称：如 财务审核员、部门经理 等
    code = Column(String(50), unique=True, nullable=False)  # 角色编码：如 finance_reviewer, department_manager
    description = Column(Text)  # 角色描述
    permissions = Column(JSON, default=[])  # 权限列表
    is_system = Column(Boolean, default=False)  # 是否系统内置角色（内置角色不可删除）
    is_active = Column(Boolean, default=True)  # 是否启用
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class UserRole(Base):
    """用户 - 角色关联表"""
    __tablename__ = "user_roles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    role_id = Column(Integer, ForeignKey("roles.id"), nullable=False)
    assigned_by = Column(Integer, ForeignKey("users.id"))  # 分配人
    assigned_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=True)  # 过期时间（可选）

    # 关联
    user = relationship("User", foreign_keys=[user_id], backref="user_roles")
    role = relationship("Role", backref="role_users")
    assigner = relationship("User", foreign_keys=[assigned_by])


# ============ 站内通知 ============
class Notification(Base):
    """站内通知表"""
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)  # 接收用户
    title = Column(String(200), nullable=False)  # 通知标题
    content = Column(Text, nullable=False)  # 通知内容
    type = Column(String(50), default="system")  # 通知类型：system(系统), workflow(工作流), task(任务) 等
    related_type = Column(String(50))  # 关联类型：application, dataset, workflow_record 等
    related_id = Column(Integer)  # 关联 ID
    is_read = Column(Boolean, default=False)  # 是否已读
    read_at = Column(DateTime(timezone=True))  # 阅读时间
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # 关联
    recipient = relationship("User", backref="notifications")


# ============ 部门管理 ============
class Department(Base):
    """部门表"""
    __tablename__ = "departments"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False)  # 部门名称
    code = Column(String(50), unique=True, nullable=False)  # 部门编码
    description = Column(Text)  # 部门描述
    parent_id = Column(Integer, ForeignKey("departments.id"), nullable=True)  # 父部门 ID
    manager_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # 部门负责人 ID
    is_active = Column(Boolean, default=True)  # 是否启用
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # 关联
    parent = relationship("Department", remote_side=[id], backref="children")
    manager = relationship("User", foreign_keys=[manager_id], backref="managed_department")
    members = relationship("User", foreign_keys="User.department_id", back_populates="department_rel")


# 更新 User 模型，添加部门关联
# 注意：需要在 User 模型中添加 department_id 字段和 department_rel 关联
# 这里我们通过迁移脚本来处理
