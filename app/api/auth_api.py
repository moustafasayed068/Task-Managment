from fastapi import APIRouter, Depends, HTTPException, Request, status, BackgroundTasks
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.db.session_db import get_db
from app.models.user_models import UserModel
from app.schemas.auth_schemas import UserRegister, Token
from app.core.security import hash_password, verify_password, create_access_token
from app.core.dependencies import get_current_user
from app.core.logger_core import logger
from app.services.email_service import send_login_failure_alert

router = APIRouter()


@router.post("/register", status_code=status.HTTP_201_CREATED)
def register(user: UserRegister, request: Request, db: Session = Depends(get_db)):
    client_ip = request.client.host if request.client else "unknown"
    try:
        new_user = UserModel(
            username=user.username,
            email=user.email,
            password_hash=hash_password(user.password),
            role="employee",
        )
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        logger.info("REGISTER SUCCESS | username={} | ip={}", user.username, client_ip)
        return {"message": "User registered successfully"}

    except IntegrityError:
        db.rollback()
        logger.warning("REGISTER FAILED | username={} | ip={} | reason=duplicate", user.username, client_ip)
        raise HTTPException(status_code=400, detail="Username or email already registered")
    except Exception as e:
        db.rollback()
        logger.error("REGISTER ERROR | username={} | ip={} | error={}", user.username, client_ip, e)
        raise HTTPException(status_code=500, detail="An internal server error occurred")


@router.post("/login", response_model=Token)
def login(
    request: Request,
    background_tasks: BackgroundTasks,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    client_ip = request.client.host if request.client else "unknown"
    user = db.query(UserModel).filter(UserModel.username == form_data.username).first()

    # ── User not found ───────────────────────────────────────────────────
    if not user:
        logger.warning(
            "AUTH FAILED | username={} | ip={} | reason=user_not_found",
            form_data.username, client_ip,
        )
        logger.info("Dispatching email alert as a background task")
        background_tasks.add_task(
            send_login_failure_alert,
            username=form_data.username,
            ip_address=client_ip,
            role=None,
            reason="Username not found in the system",
        )
        return JSONResponse(
            status_code=401, 
            content={"detail": "Invalid credentials"}, 
            background=background_tasks
        )

    # ── Wrong password ───────────────────────────────────────────────────
    if not verify_password(form_data.password, user.password_hash):
        if user.role == "admin":
            logger.critical(
                "SECURITY ALERT | Failed admin login | username={} | ip={}",
                form_data.username, client_ip,
            )
        else:
            logger.warning(
                "AUTH FAILED | username={} | role={} | ip={} | reason=wrong_password",
                form_data.username, user.role, client_ip,
            )
        logger.info("Dispatching email alert as a background task")
        background_tasks.add_task(
            send_login_failure_alert,
            username=form_data.username,
            ip_address=client_ip,
            role=user.role,
            reason=f"Wrong password for {user.role} account",
        )
        return JSONResponse(
            status_code=401, 
            content={"detail": "Invalid credentials"}, 
            background=background_tasks
        )

    # ── Success ──────────────────────────────────────────────────────────
    logger.info(
        "AUTH SUCCESS | username={} | role={} | ip={}",
        user.username, user.role, client_ip,
    )
    token = create_access_token({"sub": str(user.id), "role": user.role})
    return {"access_token": token, "token_type": "bearer"}


@router.get("/me")
def get_me(request: Request, current_user: UserModel = Depends(get_current_user)):
    client_ip = request.client.host if request.client else "unknown"
    logger.debug("ME | username={} | role={} | ip={}", current_user.username, current_user.role, client_ip)
    return {"id": current_user.id, "username": current_user.username, "role": current_user.role}