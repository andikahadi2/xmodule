from sqlalchemy import select
from sqlalchemy.orm import Session

from app.clipper.models.project import Project


def list_projects(db: Session) -> list[Project]:
    return list(db.scalars(select(Project).order_by(Project.created_at.desc())))


def create_project(db: Session, name: str) -> Project:
    project = Project(name=name)
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


def get_project(db: Session, project_id: int) -> Project | None:
    return db.get(Project, project_id)
