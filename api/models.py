from sqlalchemy import Column, BigInteger, Enum, String, Text, ForeignKey, TIMESTAMP, func
from sqlalchemy.orm import relationship
from .database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(BigInteger, primary_key=True, index=True)


class PostModeration(Base):
    __tablename__ = "posts_moderation"

    id = Column(BigInteger, primary_key=True, index=True, autoincrement=True)
    status = Column(
        Enum("reported", "request", "reviewd", "disclined", "success", name="status_enum"),
        nullable=False,
        default="reported"
    )
    url = Column(String(500), nullable=False)
    post_type = Column(
        Enum("img", "video", "audio", "text", name="post_type_enum"),
        nullable=False
    )
    table_name = Column(String(255), nullable=False)
    reason = Column(Text)
    user_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE", onupdate="CASCADE"), nullable=False)
    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())

    user = relationship("User")
