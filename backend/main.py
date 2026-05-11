from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import Session
from models import AnalyzeRequest, AnalyzeResponse
from models import GenerationRequest, GenerationResponse
from models import DeepenRequest, DeepenResponse
from engine import analyze_course, generate_exercises, deepen_exercise
from database import engine, create_db_and_tables
from auth_models import RegisterRequest, LoginRequest, AuthResponse, UserOut
from auth import hash_password, verify_password, create_token, get_user_by_email, seed_demo_accounts
from auth_models import User
import io


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        print("==> Création des tables...", flush=True)
        create_db_and_tables()
        print("==> Tables OK", flush=True)
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
        user = User(email=req.email.lower().strip(), nom=req.nom.strip(), password_hash=hash_password(req.password))
        session.add(user)
        session.commit()
        session.refresh(user)
        token = create_token(user.id, user.email, user.nom)
        return AuthResponse(token=token, user=UserOut(id=user.id, email=user.email, nom=user.nom))


@app.post("/api/auth/login", response_model=AuthResponse)
async def api_login(req: LoginRequest):
    with Session(engine) as session:
        user = get_user_by_email(session, req.email.lower().strip())
        if not user or not verify_password(req.password, user.password_hash):
            raise HTTPException(status_code=401, detail="Email ou mot de passe incorrect.")
        token = create_token(user.id, user.email, user.nom)
        return AuthResponse(token=token, user=UserOut(id=user.id, email=user.email, nom=user.nom))


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


if __name__ == "__main__":
    import uvicorn
    print("═══════════════════════════════════════")
    print("  PédaBot Backend v2 — Auth + DB")
    print("  API : http://localhost:8000")
    print("  Docs: http://localhost:8000/docs")
    print("═══════════════════════════════════════")
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
