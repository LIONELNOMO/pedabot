from pydantic import BaseModel
from typing import List, Optional

# ══════════════════════════════════════
#  REQUÊTES
# ══════════════════════════════════════

class AnalyzeRequest(BaseModel):
    courseText: str

class SectionItem(BaseModel):
    num: Optional[str] = ""
    title: str
    content: str = ""

class GenerationRequest(BaseModel):
    exName: str
    sections: List[SectionItem]
    difficulty: str   # facile, moyen, difficile, progressif
    lang: str         # algo, python, javascript
    appro: bool
    courseText: Optional[str] = ""

class DeepenRequest(BaseModel):
    exerciseTitle: str
    lang: str         # algo, python, javascript
    section: Optional[SectionItem] = None

# ══════════════════════════════════════
#  RÉPONSES
# ══════════════════════════════════════

class AnalyzeResponse(BaseModel):
    lang: str
    langLabel: str
    sections: List[SectionItem]

class ExerciseOutput(BaseModel):
    level: str
    title: str
    body: str
    code: Optional[str] = None
    section: Optional[SectionItem] = None

class GenerationResponse(BaseModel):
    exercises: List[ExerciseOutput]

class DeepenResponse(BaseModel):
    exercise: ExerciseOutput
