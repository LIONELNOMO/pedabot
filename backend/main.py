from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from models import AnalyzeRequest, AnalyzeResponse
from models import GenerationRequest, GenerationResponse
from models import DeepenRequest, DeepenResponse
from engine import analyze_course, generate_exercises, deepen_exercise

app = FastAPI(title="PédaBot — Backend Python Engine")

# Autoriser React (Vite) à communiquer avec l'API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    return {"status": "ok", "name": "PédaBot Backend", "version": "1.0"}


@app.post("/api/analyze", response_model=AnalyzeResponse)
async def api_analyze(req: AnalyzeRequest):
    """Moteur 1+2 : Analyse le texte du cours → sections + syntaxe."""
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
    """Moteur 3 : Génère les exercices à partir des paramètres du wizard."""
    try:
        results = await generate_exercises(req)
        return GenerationResponse(exercises=results)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/deepen", response_model=DeepenResponse)
async def api_deepen(req: DeepenRequest):
    """Moteur 4 : Génère une version approfondie d'un exercice existant."""
    try:
        result = await deepen_exercise(req)
        return DeepenResponse(exercise=result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ══════════════════════════════════════
#  Permet de lancer avec : python main.py
# ══════════════════════════════════════
if __name__ == "__main__":
    import uvicorn
    print("═══════════════════════════════════════")
    print("  PédaBot Backend — Démarrage...")
    print("  API : http://localhost:8000")
    print("  Docs: http://localhost:8000/docs")
    print("═══════════════════════════════════════")
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
