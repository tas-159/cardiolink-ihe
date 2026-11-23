"""Login / session. Maps to IHE ATNA: every attempt is audited (ITI-20)."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select

from ..audit import write_audit
from ..database import get_session
from ..models import User
from ..schemas import LoginRequest, TokenOut, UserOut
from ..security import create_access_token, get_current_user, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenOut)
def login(body: LoginRequest, session: Session = Depends(get_session)):
    identifier = body.identifier.strip().upper()
    user = session.exec(select(User).where(User.identifier == identifier)).first()
    if not user or not verify_password(body.password, user.password_hash):
        write_audit(session, actor=identifier or "inconnu",
                    action="Connexion refusée", result="Refusé")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Identifiant ou mot de passe incorrect.",
        )
    token = create_access_token(user.identifier)
    write_audit(session, actor=user.name, action="Connexion", result="Autorisé")
    return TokenOut(
        access_token=token,
        user=UserOut(identifier=user.identifier, name=user.name,
                     role=user.role, initials=user.initials),
    )


@router.get("/me", response_model=UserOut)
def me(current: User = Depends(get_current_user)):
    return UserOut(identifier=current.identifier, name=current.name,
                   role=current.role, initials=current.initials)
