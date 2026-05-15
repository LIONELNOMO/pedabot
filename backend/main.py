from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, UploadFile, File, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import Session, select
from models import AnalyzeRequest, AnalyzeResponse
from models import GenerationRequest, GenerationResponse
from models import DeepenRequest, DeepenResponse
from models import ShareExerciseRequest, AssignRequest, SubmitRequest
from engine import analyze_course, generate_exercises, deepen_exercise
from database import engine, create_db_and_tables
from auth_models import RegisterRequest, LoginRequest, AuthResponse, UserOut
from auth_models import User, ExerciseDB, SharedLink, Submission, Assignment
from auth import hash_password, verify_password, create_token, get_user_by_email, seed_demo_accounts, decode_token
import io, json, secrets


def run_migrations():
    """Migrations manuelles pour les colonnes ajoutées sur DB existante (SQLite + PostgreSQL)."""
    from sqlalchemy import text
    with engine.connect() as conn:
        # Ajouter colonne 'role' à la table user si elle n'existe pas
        try:
            conn.execute(text("ALTER TABLE \"user\" ADD COLUMN role VARCHAR DEFAULT 'prof'"))
            conn.commit()
            print("==> Migration : colonne 'role' ajoutée à user", flush=True)
        except Exception:
            conn.rollback()
            # Colonne déjà présente — normal, on ignore
            pass


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        print("==> Création des tables...", flush=True)
        create_db_and_tables()
        print("==> Tables OK", flush=True)
        run_migrations()
        with Session(engine) as session:
            seed_demo_accounts(session)
        print("==> Comptes démo OK", flush=True)
    except Exception as e:
        import traceback
        print(f"==> ERREUR DEMARRAGE : {e}", flush=True)
        traceback.print_exc()
        raise
    yield


app = FastAPI(title="PédaBot — Backend Python Engine", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    return {"status": "ok", "name": "PédaBot Backend", "version": "2.0"}


# ══════════════════════════════════════
#  AUTH
# ══════════════════════════════════════

@app.post("/api/auth/register", response_model=AuthResponse)
async def api_register(req: RegisterRequest):
    with Session(engine) as session:
        if get_user_by_email(session, req.email):
            raise HTTPException(status_code=409, detail="Un compte existe déjà avec cet email.")
        if len(req.password) < 6:
            raise HTTPException(status_code=400, detail="Le mot de passe doit faire au moins 6 caractères.")
        role = req.role if req.role in ('prof', 'eleve') else 'prof'
        user = User(email=req.email.lower().strip(), nom=req.nom.strip(), password_hash=hash_password(req.password), role=role)
        session.add(user)
        session.commit()
        session.refresh(user)
        token = create_token(user.id, user.email, user.nom, user.role)
        return AuthResponse(token=token, user=UserOut(id=user.id, email=user.email, nom=user.nom, role=user.role))


@app.post("/api/auth/login", response_model=AuthResponse)
async def api_login(req: LoginRequest):
    with Session(engine) as session:
        user = get_user_by_email(session, req.email.lower().strip())
        if not user or not verify_password(req.password, user.password_hash):
            raise HTTPException(status_code=401, detail="Email ou mot de passe incorrect.")
        token = create_token(user.id, user.email, user.nom, user.role)
        return AuthResponse(token=token, user=UserOut(id=user.id, email=user.email, nom=user.nom, role=user.role))


# ══════════════════════════════════════
#  EXTRACTION FICHIERS
# ══════════════════════════════════════

@app.post("/api/extract")
async def api_extract(file: UploadFile = File(...)):
    content = await file.read()
    filename = file.filename.lower()
    text = ""
    try:
        if filename.endswith(".pdf"):
            import pdfplumber
            with pdfplumber.open(io.BytesIO(content)) as pdf:
                pages = [p.extract_text() or "" for p in pdf.pages]
            text = "\n\n".join(p.strip() for p in pages if p.strip())
        elif filename.endswith(".docx"):
            from docx import Document
            doc = Document(io.BytesIO(content))
            text = "\n".join(p.text for p in doc.paragraphs if p.text.strip())
        elif filename.endswith(".doc"):
            raise HTTPException(status_code=400, detail="Format .doc non supporté. Convertissez en .docx.")
        elif filename.endswith(".txt"):
            text = content.decode("utf-8", errors="ignore")
        else:
            raise HTTPException(status_code=400, detail="Format non supporté. Utilisez PDF, DOCX ou TXT.")
        if not text.strip():
            raise HTTPException(status_code=422, detail="Aucun texte lisible trouvé dans ce fichier.")
        return {"text": text.strip()}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur extraction : {str(e)}")


# ══════════════════════════════════════
#  MOTEUR PÉDAGOGIQUE
# ══════════════════════════════════════

@app.post("/api/analyze", response_model=AnalyzeResponse)
async def api_analyze(req: AnalyzeRequest):
    try:
        if len(req.courseText.strip()) < 20:
            raise HTTPException(status_code=400, detail="Le texte du cours est trop court.")
        return await analyze_course(req)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/generate", response_model=GenerationResponse)
async def api_generate(req: GenerationRequest):
    try:
        results = await generate_exercises(req)
        return GenerationResponse(exercises=results)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/deepen", response_model=DeepenResponse)
async def api_deepen(req: DeepenRequest):
    try:
        result = await deepen_exercise(req)
        return DeepenResponse(exercise=result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ══════════════════════════════════════
#  HELPER AUTH
# ══════════════════════════════════════

def require_teacher(authorization: str = Header(...)):
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Token manquant.")
    payload = decode_token(authorization[7:])
    if not payload:
        raise HTTPException(status_code=401, detail="Token invalide ou expiré.")
    return payload


# ══════════════════════════════════════
#  ASSIGNATION EXERCICES ÉLÈVES
# ══════════════════════════════════════

@app.get("/api/eleves")
async def api_get_eleves(payload=Depends(require_teacher)):
    with Session(engine) as session:
        eleves = session.exec(select(User).where(User.role == 'eleve')).all()
        return [{"id": e.id, "nom": e.nom, "email": e.email} for e in eleves]


@app.post("/api/exercises/share")
async def api_share_exercise(req: ShareExerciseRequest, payload=Depends(require_teacher)):
    with Session(engine) as session:
        ex = ExerciseDB(
            teacher_id  = int(payload["sub"]),
            teacher_nom = payload["nom"],
            titre       = req.titre,
            contenu     = json.dumps(req.exercise, ensure_ascii=False),
            lang        = req.lang,
            difficulty  = req.difficulty,
        )
        session.add(ex)
        session.commit()
        session.refresh(ex)
        token = secrets.token_urlsafe(6)
        link  = SharedLink(token=token, exercise_id=ex.id, teacher_id=int(payload["sub"]))
        session.add(link)
        session.commit()
        return {"token": token}


@app.get("/api/eleve/{token}")
async def api_eleve_view(token: str):
    with Session(engine) as session:
        link = session.get(SharedLink, token)
        if not link:
            raise HTTPException(status_code=404, detail="Lien invalide ou introuvable.")
        ex = session.get(ExerciseDB, link.exercise_id)
        if not ex:
            raise HTTPException(status_code=404, detail="Exercice introuvable.")
        return {
            "token":       token,
            "titre":       ex.titre,
            "teacher_nom": ex.teacher_nom,
            "exercise":    json.loads(ex.contenu),
            "lang":        ex.lang,
            "difficulty":  ex.difficulty,
        }


@app.post("/api/eleve/{token}/submit")
async def api_eleve_submit(token: str, req: SubmitRequest):
    with Session(engine) as session:
        if not session.get(SharedLink, token):
            raise HTTPException(status_code=404, detail="Lien invalide.")
        sub = Submission(token=token, eleve_prenom=req.eleve_prenom, reponses=req.reponses)
        session.add(sub)
        session.commit()
        return {"success": True}


@app.get("/api/eleve/{token}/submissions")
async def api_get_submissions(token: str, payload=Depends(require_teacher)):
    with Session(engine) as session:
        link = session.get(SharedLink, token)
        if not link or link.teacher_id != int(payload["sub"]):
            raise HTTPException(status_code=403, detail="Accès refusé.")
        subs = session.exec(select(Submission).where(Submission.token == token)).all()
        return [{"eleve_prenom": s.eleve_prenom, "reponses": s.reponses, "submitted_at": s.submitted_at.isoformat()} for s in subs]


@app.get("/api/exercises/mine")
async def api_my_exercises(payload=Depends(require_teacher)):
    with Session(engine) as session:
        links = session.exec(select(SharedLink).where(SharedLink.teacher_id == int(payload["sub"]))).all()
        result = []
        for link in links:
            ex    = session.get(ExerciseDB, link.exercise_id)
            count = len(session.exec(select(Submission).where(Submission.token == link.token)).all())
            result.append({
                "token":            link.token,
                "titre":            ex.titre if ex else "Exercice supprimé",
                "submission_count": count,
                "created_at":       link.created_at.isoformat(),
                "difficulty":       ex.difficulty if ex else "",
            })
        return sorted(result, key=lambda x: x["created_at"], reverse=True)


@app.post("/api/exercises/assign")
async def api_assign_exercise(req: AssignRequest, payload=Depends(require_teacher)):
    created = []
    with Session(engine) as session:
        for email in req.emails:
            email = email.strip().lower()
            if not email:
                continue
            a = Assignment(
                teacher_id  = int(payload["sub"]),
                teacher_nom = payload["nom"],
                eleve_email = email,
                titre       = req.titre,
                contenu     = json.dumps(req.exercise, ensure_ascii=False),
                lang        = req.lang,
                difficulty  = req.difficulty,
            )
            session.add(a)
            created.append(email)
        session.commit()
    return {"assigned_to": created}


@app.get("/api/mes-exercices")
async def api_mes_exercices(payload=Depends(require_teacher)):
    email = payload["email"]
    with Session(engine) as session:
        assignments = session.exec(
            select(Assignment).where(Assignment.eleve_email == email)
        ).all()
        return [
            {
                "id":           a.id,
                "titre":        a.titre,
                "teacher_nom":  a.teacher_nom,
                "lang":         a.lang,
                "difficulty":   a.difficulty,
                "submitted":    a.submitted_at is not None,
                "submitted_at": a.submitted_at.isoformat() if a.submitted_at else None,
                "corrige_visible": a.corrige_visible,
                "created_at":   a.created_at.isoformat(),
            }
            for a in sorted(assignments, key=lambda x: x.created_at, reverse=True)
        ]


@app.get("/api/exercice/{assignment_id}")
async def api_get_exercice(assignment_id: int, payload=Depends(require_teacher)):
    email = payload["email"]
    with Session(engine) as session:
        a = session.get(Assignment, assignment_id)
        if not a or a.eleve_email != email:
            raise HTTPException(status_code=403, detail="Accès refusé.")
        return {
            "id":              a.id,
            "titre":           a.titre,
            "teacher_nom":     a.teacher_nom,
            "exercise":        json.loads(a.contenu),
            "lang":            a.lang,
            "difficulty":      a.difficulty,
            "submitted":       a.submitted_at is not None,
            "reponses":        a.reponses,
            "corrige_visible": a.corrige_visible,
        }


@app.post("/api/exercice/{assignment_id}/submit")
async def api_submit_exercice(assignment_id: int, req: SubmitRequest, payload=Depends(require_teacher)):
    email = payload["email"]
    with Session(engine) as session:
        a = session.get(Assignment, assignment_id)
        if not a or a.eleve_email != email:
            raise HTTPException(status_code=403, detail="Accès refusé.")
        if a.submitted_at:
            raise HTTPException(status_code=400, detail="Déjà soumis.")
        from datetime import datetime as dt
        a.reponses     = req.reponses
        a.submitted_at = dt.utcnow()
        session.add(a)
        session.commit()
        return {"success": True}


@app.get("/api/exercises/mine")
async def api_my_exercises(payload=Depends(require_teacher)):
    with Session(engine) as session:
        assignments = session.exec(
            select(Assignment).where(Assignment.teacher_id == int(payload["sub"]))
        ).all()
        result = {}
        for a in assignments:
            key = a.titre
            if key not in result:
                result[key] = {"titre": a.titre, "difficulty": a.difficulty, "eleves": [], "created_at": a.created_at.isoformat()}
            result[key]["eleves"].append({
                "eleve_email":  a.eleve_email,
                "submitted":    a.submitted_at is not None,
                "submitted_at": a.submitted_at.isoformat() if a.submitted_at else None,
                "reponses":     a.reponses,
                "assignment_id": a.id,
            })
        return sorted(result.values(), key=lambda x: x["created_at"], reverse=True)


if __name__ == "__main__":
    import uvicorn
    print("═══════════════════════════════════════")
    print("  PédaBot Backend v2 — Auth + DB")
    print("  API : http://localhost:8000")
    print("  Docs: http://localhost:8000/docs")
    print("═══════════════════════════════════════")
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
