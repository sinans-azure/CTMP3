import os
import bcrypt
from datetime import datetime
from sqlalchemy import create_engine, Column, String, Integer, DateTime, ForeignKey, Table, Float
from sqlalchemy.orm import declarative_base, sessionmaker, relationship

DATABASE_URL = os.environ.get("DATABASE_URL") or os.environ.get("PG_CONNECTION_STRING") or "sqlite:///shared_ctmp.db"

if DATABASE_URL.startswith("sqlite"):
    db_path = DATABASE_URL
    if db_path == "sqlite:///shared_ctmp.db":
        db_path = "sqlite:///../shared_ctmp.db"
    engine = create_engine(db_path, connect_args={"check_same_thread": False})
else:
    if "sslmode" not in DATABASE_URL:
        if "?" in DATABASE_URL:
            DATABASE_URL += "&sslmode=require"
        else:
            DATABASE_URL += "?sslmode=require"
    engine = create_engine(DATABASE_URL, pool_pre_ping=True)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

user_group_association = Table(
    "user_group_association",
    Base.metadata,
    Column("user_id", String, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
    Column("group_id", String, ForeignKey("training_groups.id", ondelete="CASCADE"), primary_key=True)
)

class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String, nullable=False)
    name = Column(String)
    role = Column(String, nullable=False) # "Admin", "Trainer", "Student"
    created_at = Column(DateTime, default=datetime.utcnow)
    invite_token = Column(String, unique=True, index=True, nullable=True)

    groups = relationship("TrainingGroup", secondary=user_group_association, back_populates="students")

    def verify_password(self, password: str) -> bool:
        return bcrypt.checkpw(password.encode('utf-8'), self.hashed_password.encode('utf-8'))

    @staticmethod
    def hash_password(password: str) -> str:
        return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

class TrainingGroup(Base):
    __tablename__ = "training_groups"

    id = Column(String, primary_key=True, index=True)
    name = Column(String, nullable=False)
    description = Column(String)
    trainer_id = Column(String, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    aws_account_id = Column(String)
    aws_region = Column(String, default="us-east-1")
    created_at = Column(DateTime, default=datetime.utcnow)

    trainer = relationship("User", foreign_keys=[trainer_id])
    students = relationship("User", secondary=user_group_association, back_populates="groups")
    instances = relationship("EC2Instance", back_populates="group", cascade="all, delete-orphan")

class EC2Instance(Base):
    __tablename__ = "ec2_instances"

    id = Column(String, primary_key=True, index=True)
    name = Column(String)
    state = Column(String, default="stopped")
    instance_type = Column(String, default="t3.micro")
    launch_time = Column(DateTime, default=datetime.utcnow)
    group_id = Column(String, ForeignKey("training_groups.id", ondelete="CASCADE"), nullable=False)
    student_id = Column(String, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    group = relationship("TrainingGroup", back_populates="instances")
    student = relationship("User")

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(String, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    actor_id = Column(String)
    actor_name = Column(String)
    action = Column(String)
    resource_type = Column(String)
    resource_id = Column(String)
    details = Column(String)

def init_db():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        if db.query(User).count() == 0:
            # Seed Alice (Admin)
            admin = User(
                id="user-001",
                username="admin1",
                email="alice@contoso.com",
                hashed_password=User.hash_password("Password123"),
                name="Alice Johnson",
                role="Admin"
            )
            # Seed Bob (Trainer)
            trainer = User(
                id="user-002",
                username="trainer1",
                email="bob@contoso.com",
                hashed_password=User.hash_password("Password123"),
                name="Bob Smith",
                role="Trainer"
            )
            # Seed Carol (Student)
            student1 = User(
                id="user-003",
                username="student1",
                email="carol@contoso.com",
                hashed_password=User.hash_password("Password123"),
                name="Carol Williams",
                role="Student"
            )
            # Seed Dave (Student)
            student2 = User(
                id="user-004",
                username="student2",
                email="dave@contoso.com",
                hashed_password=User.hash_password("Password123"),
                name="Dave Brown",
                role="Student"
            )
            db.add_all([admin, trainer, student1, student2])
            db.commit()
            
            # Seed some default groups
            g1 = TrainingGroup(
                id="group-101",
                name="AWS Basics - Group A",
                description="Introduction to AWS infrastructure.",
                trainer_id="user-002",
                aws_account_id="123456789012",
                aws_region="us-east-1"
            )
            g2 = TrainingGroup(
                id="group-102",
                name="Advanced Cloud Architecture",
                description="Complex architectures and OIDC federation.",
                trainer_id="user-002",
                aws_account_id="123456789012",
                aws_region="us-west-2"
            )
            db.add_all([g1, g2])
            db.commit()
            
            # Map students to groups
            g1.students.append(student1)
            g1.students.append(student2)
            g2.students.append(student1)
            db.commit()
            
            # Seed default EC2 instances
            inst1 = EC2Instance(
                id="i-0abcdef1234567890",
                name="student-web-server",
                state="running",
                instance_type="t3.micro",
                group_id="group-101",
                student_id="user-003"
            )
            inst2 = EC2Instance(
                id="i-0123456789abcdef0",
                name="student-db-server",
                state="stopped",
                instance_type="t3.medium",
                group_id="group-101",
                student_id="user-004"
            )
            inst3 = EC2Instance(
                id="i-0987654321fedcba0",
                name="adv-k8s-node",
                state="running",
                instance_type="t3.large",
                group_id="group-102",
                student_id="user-003"
            )
            db.add_all([inst1, inst2, inst3])
            db.commit()
    except Exception as e:
        print(f"Error seeding DB: {e}")
        db.rollback()
    finally:
        db.close()
