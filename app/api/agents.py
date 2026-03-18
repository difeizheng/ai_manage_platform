"""
智能体管理 API
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.core.database import get_db
from app.models.models import Agent, User, ApplicationRequest
from app.schemas.schemas import AgentCreate, AgentUpdate, AgentResponse, ApplicationRequestCreate
from app.api.auth import get_current_user

router = APIRouter()


@router.get("/", response_model=List[AgentResponse])
def list_agents(
    skip: int = 0,
    limit: int = 100,
    agent_type: str = None,
    business_domain: str = None,
    db: Session = Depends(get_db)
):
    """获取智能体列表"""
    query = db.query(Agent)

    if agent_type:
        query = query.filter(Agent.agent_type == agent_type)
    if business_domain:
        query = query.filter(Agent.business_domain == business_domain)

    agents = query.offset(skip).limit(limit).all()
    return agents


@router.get("/{agent_id}", response_model=AgentResponse)
def get_agent(agent_id: int, db: Session = Depends(get_db)):
    """获取智能体详情"""
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="智能体不存在")
    return agent


@router.post("/", response_model=AgentResponse)
def create_agent(
    agent_data: AgentCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """创建智能体"""
    agent = Agent(
        **agent_data.model_dump(),
        creator_id=current_user.id,
        status="available"
    )
    db.add(agent)
    db.commit()
    db.refresh(agent)
    return agent


@router.put("/{agent_id}", response_model=AgentResponse)
def update_agent(
    agent_id: int,
    agent_data: AgentUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """更新智能体"""
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="智能体不存在")

    update_data = agent_data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(agent, key, value)

    db.commit()
    db.refresh(agent)
    return agent


@router.delete("/{agent_id}")
def delete_agent(
    agent_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """删除智能体"""
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="智能体不存在")

    if agent.creator_id != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="无权限删除此智能体")

    db.delete(agent)
    db.commit()
    return {"message": "删除成功"}


@router.post("/{agent_id}/request")
def request_agent_access(
    agent_id: int,
    request_data: ApplicationRequestCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """申请智能体使用权限"""
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="智能体不存在")

    request = ApplicationRequest(
        request_type="agent",
        resource_id=agent_id,
        resource_name=agent.name,
        applicant_id=current_user.id,
        applicant_department=current_user.department,
        purpose=request_data.purpose,
        expected_duration=request_data.expected_duration,
        expected_frequency=request_data.expected_frequency,
        related_application=request_data.related_application,
        status="pending"
    )
    db.add(request)
    db.commit()
    db.refresh(request)

    return {"message": "申请已提交", "request_id": request.id}
