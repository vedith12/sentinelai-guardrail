import yaml
from pathlib import Path
from sqlmodel import SQLModel, create_engine, Session, select
from app.config import settings
from app.models import Policy

engine = create_engine(settings.DATABASE_URL, echo=False)

def init_db():
    # Create database tables
    SQLModel.metadata.create_all(engine)
    
    # Load default policies from policies.yaml if the table is empty
    with Session(engine) as session:
        statement = select(Policy)
        existing_policies = session.exec(statement).first()
        if not existing_policies:
            yaml_path = Path(__file__).parent / "policies" / "policies.yaml"
            if yaml_path.exists():
                with open(yaml_path, "r") as f:
                    data = yaml.safe_load(f)
                    for policy_data in data.get("policies", []):
                        policy = Policy(
                            name=policy_data["name"],
                            category=policy_data["category"],
                            description=policy_data["description"],
                            severity=policy_data["severity"],
                            action=policy_data["action"],
                            detection_strategy=policy_data["detection_strategy"],
                            rules=policy_data.get("rules"),
                            examples=policy_data.get("examples"),
                            is_active=True
                        )
                        session.add(policy)
                session.commit()

def get_session():
    with Session(engine) as session:
        yield session
