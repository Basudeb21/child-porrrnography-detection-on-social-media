from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from .. import schemas, crud
from ..database import SessionLocal

router = APIRouter(prefix="/moderation", tags=["Moderation"])

# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/", response_model=schemas.PostModerationResponse)
def create_post(post: schemas.PostModerationCreate, db: Session = Depends(get_db)):
    return crud.create_post_moderation(db=db, post=post)

@router.get("/", response_model=list[schemas.PostModerationResponse])
def read_moderations(skip: int = 0, limit: int = 10, db: Session = Depends(get_db)):
    return crud.get_moderations(db, skip=skip, limit=limit)

@router.get("/{moderation_id}", response_model=schemas.PostModerationResponse)
def read_moderation(moderation_id: int, db: Session = Depends(get_db)):
    db_post = crud.get_moderation_by_id(db, moderation_id=moderation_id)
    if not db_post:
        raise HTTPException(status_code=404, detail="Moderation not found")
    return db_post
