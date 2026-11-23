"""Login / session + account management. Maps to IHE ATNA: audited (ITI-20)."""
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select

from ..audit import write_audit
from ..database import get_session
from ..models import User
from ..schemas import LoginRequest, TokenOut, UserCreate, UserOut
from ..security import create_access_token, get_current_user, hash_password, verify_password

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


# --- Account management (admin-style: only a logged-in user can manage) ---
@router.get("/users", response_model=List[UserOut])
def list_users(session: Session = Depends(get_session),
               current: User = Depends(get_current_user)):
    users = session.exec(select(User)).all()
    return [UserOut(identifier=u.identifier, name=u.name, role=u.role, initials=u.initials)
            for u in users]


@router.post("/users", response_model=UserOut, status_code=201)
def create_user(body: UserCreate, session: Session = Depends(get_session),
                current: User = Depends(get_current_user)):
    identifier = body.identifier.strip().upper()
    if not identifier or not body.password or not body.name.strip():
        raise HTTPException(status_code=400, detail="Identifiant, nom et mot de passe sont requis.")
    if session.exec(select(User).where(User.identifier == identifier)).first():
        raise HTTPException(status_code=409, detail="Cet identifiant existe déjà.")
    initials = (body.initials or "".join(w[0] for w in body.name.split()[:2])).upper()[:2] or "??"
    user = User(
        identifier=identifier, password_hash=hash_password(body.password),
        name=body.name.strip(), role=body.role.strip() or "Utilisateur", initials=initials,
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    write_audit(session, actor=current.name,
                action=f"Création compte {identifier}", result="Validé")
    return UserOut(identifier=user.identifier, name=user.name,
                   role=user.role, initials=user.initials)
