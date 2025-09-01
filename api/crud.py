from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from fastapi import HTTPException
from . import models, schemas

def create_post_moderation(db: Session, post: schemas.PostModerationCreate):
    if not post.user_id or post.user_id <= 0:
        post.user_id = 24  

    new_post = models.PostModeration(**post.dict())

    try:
        db.add(new_post)
        db.commit()
        db.refresh(new_post)
        return new_post

    except IntegrityError as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"DB integrity error: {str(e.orig)}")

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")
