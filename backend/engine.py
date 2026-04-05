import re
from models import AnalyzeRequest, AnalyzeResponse, SectionItem
from models import GenerationRequest, ExerciseOutput
from models import DeepenRequest

# ══════════════════════════════════════════════════════════════
#  MOTEUR 1 — DÉTECTION DES SECTIONS
#  Patterns : Chiffres romains, arabes, lettres, mots-clés, Markdown
# ══════════════════════════════════════════════════════════════

def detect_sections(txt: str) -> list[SectionItem]:
    """Détecte les sections numérotées dans un texte de cours."""
    lines = txt.split('\n')
    PATS = [
        (re.compile(r'^(I{1,3}V?|VI{0,3}|IX|X{1,3})[.)]\s+(.+)', re.IGNORECASE), 0, 1),
        (re.compile(r'^(\d{1,2})[.)]\s+([A-ZÀÂÉÈÊÙÛÇ].{2,})'), 0, 1),
        (re.compile(r'^([A-Z])[.)]\s+([A-ZÀÂÉÈÊÙÛÇ].{2,})'), 0, 1),
        (re.compile(r'^(Chapitre|Partie|Section)\s+\d[^:]*[:\-]\s*(.+)', re.IGNORECASE), 0, 1),
        (re.compile(r'^#{1,3}\s+(.+)'), None, 0),
    ]

    secs = []
    cur = None
    body = ''

    for line in lines:
        l = line.strip()
        if not l:
            continue
        hit = False
        for pattern, n_idx, t_idx in PATS:
            m = pattern.match(l)
            if m:
                if cur:
                    cur.content = body.strip()
                    secs.append(cur)
                num = m.group(n_idx + 1) if n_idx is not None else ''
                title = m.group(t_idx + 1) if (t_idx + 1) <= len(m.groups()) else l
                cur = SectionItem(num=num, title=title.strip(), content='')
                body = ''
                hit = True
                break
        if not hit and cur:
            body += ' ' + l

    if cur:
        cur.content = body.strip()
        secs.append(cur)

    return secs[:7]


# ══════════════════════════════════════════════════════════════
#  MOTEUR 2 — DÉTECTION DE SYNTAXE
#  Analyse de fréquence de mots-clés algorithmiques / Python / JS
# ══════════════════════════════════════════════════════════════

def detect_lang(txt: str) -> tuple[str, str]:
    """Détecte le langage. Retourne (code, label)."""
    t = txt.lower()

    algo_count = len(re.findall(r'tant que|répéter|jusqu\'à|début|fin|écrire|lire|algorithme|pour.*faire', t))
    py_count = len(re.findall(r'def |print\(|import |while |for .+in|if __name__|range\(', t))
    js_count = len(re.findall(r'function |console\.|const |let |var |=>', t))

    if algo_count >= py_count and algo_count >= js_count:
        return 'algo', 'Algorithmique'
    if py_count >= js_count:
        return 'python', 'Python'
    return 'javascript', 'JavaScript'


async def analyze_course(req: AnalyzeRequest) -> AnalyzeResponse:
    """Point d'entrée : analyse du cours."""
    lang_code, lang_label = detect_lang(req.courseText)
    sections = detect_sections(req.courseText)
    return AnalyzeResponse(lang=lang_code, langLabel=lang_label, sections=sections)


# ══════════════════════════════════════════════════════════════
#  MOTEUR 5 — DÉTECTION DE DÉFINITIONS
#  Analyse les phrases du cours → génère "Qu'est-ce que… ?"
# ══════════════════════════════════════════════════════════════

# ── Articles français (pour capturer le mot-clé après l'article) ──
_ART = r"(?:[UuDd](?:n|ne|es)\s+|[Ll](?:e|a|es)\s+|[Ll][''']|[Cc](?:e(?:tte|t)?|es)\s+)"

# ── LEXIQUE A : le mot-clé est AVANT le marqueur ──
# Phrase type : "Un algorithme est une suite d'instructions…"
_MARKERS_BEFORE = [
    # === Verbe ÊTRE + article ===
    r"est\s+un(?:e)?\b",
    r"est\s+l(?:e|a|['''])\b",
    r"est\s+des\b",
    # === Verbe ÊTRE + qualificatif ===
    r"est\s+définie?\s+comme",
    r"est\s+appelée?",
    r"est\s+considérée?\s+comme",
    r"est\s+connue?\s+(?:sous\s+le\s+nom\s+de|comme)",
    r"est\s+aussi\s+(?:appelée?|connue?\s+(?:comme|sous))",
    r"est\s+(?:un|une)\s+(?:type|forme|sorte|catégorie|ensemble)\s+de",
    r"est\s+(?:également|aussi)\s+(?:un|une)\b",
    r"est\s+utilisée?\s+pour",
    r"est\s+employée?\s+pour",
    # === Verbes de définition ===
    r"représente",
    r"désigne",
    r"constitue",
    r"signifie",
    r"caractérise",
    # === Locutions verbales ===
    r"correspond(?:ent)?\s+à",
    r"consiste\s+(?:à|en)",
    r"se\s+définit\s+comme",
    r"se\s+caractérise\s+par",
    r"se\s+compose\s+de",
    r"se\s+traduit\s+par",
    r"se\s+distingue\s+par",
    r"fait\s+référence\s+à",
    r"renvoie\s+à",
    r"s[''']apparente\s+à",
    # === Rôle / Fonction ===
    r"(?:permet|sert)\s+(?:à|de)",
    r"a\s+pour\s+(?:rôle|but|objectif|fonction|mission)",
    r"vise\s+à",
    # === Définition explicite ===
    r"peut\s+(?:être|se)\s+définie?\s+comme",
    r"porte\s+le\s+nom\s+de",
]

# ── LEXIQUE B : le mot-clé est APRÈS le marqueur ──
# Phrase type : "On appelle algorithme une suite d'instructions…"
_MARKERS_AFTER = [
    r"[Oo]n\s+appelle",
    r"[Oo]n\s+définit",
    r"[Oo]n\s+nomme",
    r"[Oo]n\s+entend\s+par",
    r"[Oo]n\s+désigne\s+par",
    r"[Oo]n\s+note",
    r"[Oo]n\s+parle\s+(?:de|d['''])",
    r"[Oo]n\s+utilise\s+le\s+terme",
    r"[Ll]e\s+terme",
    r"[Ll]a\s+notion\s+de",
    r"[Ll]e\s+concept\s+de",
    r"[Ll]e\s+mot",
]

# ── Titres de section qui signalent des définitions ──
_TITLE_DEF_MARKERS = [
    r"définitions?", r"concepts?", r"notions?", r"vocabulaire",
    r"terminologie", r"glossaire", r"rappels?", r"généralités",
    r"introduction", r"pré-?requis", r"présentation",
]


def _clean_keyword(kw: str) -> str:
    """Nettoie un mot-clé extrait."""
    kw = kw.strip().rstrip(',.;:!?').strip()
    kw = re.sub(r'\s+', ' ', kw)
    # Retirer article résiduel en début
    kw = re.sub(r"^(?:un|une|le|la|l[''']|les|des|du|d[''']|ce|cette|ces)\s+", '', kw, flags=re.IGNORECASE)
    return kw.strip()


def _build_question(keyword: str, sentence: str) -> str:
    """Formule 'Qu'est-ce qu'un/une [keyword] ?' avec le bon article."""
    s_low = sentence.lower()
    kw_low = keyword.lower()
    first = kw_low[0] if kw_low else ''
    vowel = first in 'aeéèêëiïîoôuùûyh'

    # Chercher si le cours utilisait "une" → féminin
    if re.search(rf'\bune\s+{re.escape(kw_low)}', s_low):
        return f"Qu'est-ce qu'une {keyword} ?" if vowel else f"Qu'est-ce qu'une {keyword} ?"
    # Masculin ou voyelle
    if vowel:
        return f"Qu'est-ce qu'un {keyword} ?"
    return f"Qu'est-ce qu'un {keyword} ?"


def detect_definitions(text: str) -> list[dict]:
    """
    Analyse un texte de cours et extrait des questions de définition.
    Retourne [{"keyword": ..., "question": ..., "sentence": ...}, ...]
    """
    sentences = re.split(r'[.!?\n;]+', text)
    results = []
    seen = set()

    for sentence in sentences:
        s = sentence.strip()
        if len(s) < 15:
            continue

        # ── TYPE A : mot-clé AVANT le marqueur ──
        found = False
        for marker in _MARKERS_BEFORE:
            pattern = rf"({_ART}.+?)\s+{marker}"
            m = re.search(pattern, s, re.IGNORECASE)
            if m:
                raw = m.group(1).strip()
                keyword = _clean_keyword(raw)
                if 1 <= len(keyword.split()) <= 4 and keyword.lower() not in seen:
                    seen.add(keyword.lower())
                    results.append({
                        "keyword": keyword,
                        "question": _build_question(keyword, s),
                        "sentence": s.strip()
                    })
                    found = True
                break
        if found:
            continue

        # ── TYPE B : mot-clé APRÈS le marqueur ──
        for marker in _MARKERS_AFTER:
            pattern = rf"{marker}\s+(?:{_ART})?(.+?)(?:\s+(?:un|une|le|la|l[''']|comme|tout|ce|qui|,|$))"
            m = re.search(pattern, s, re.IGNORECASE)
            if m:
                keyword = _clean_keyword(m.group(1))
                if 1 <= len(keyword.split()) <= 4 and keyword.lower() not in seen:
                    seen.add(keyword.lower())
                    results.append({
                        "keyword": keyword,
                        "question": _build_question(keyword, s),
                        "sentence": s.strip()
                    })
                break

    return results


def _make_definition_trous(sentence: str, keyword: str) -> str:
    """Remplace le mot-clé dans la phrase par des __________ pour créer un texte à trous."""
    pattern = re.compile(re.escape(keyword), re.IGNORECASE)
    return pattern.sub('__________', sentence)


def _make_pattern_trous(sentence: str, keyword: str, pat_type: str, data_item: dict) -> str:
    """Crée un texte à trous adapté au type de pattern.
    - date → cache la date
    - fonction → cache la description de la fonction (après le marqueur)
    - exemple → cache les exemples listés
    - autres → cache le mot-clé (sujet)
    """
    # ── DATES : cacher la date, pas le sujet ──
    if pat_type == 'date' and data_item.get('date'):
        return re.sub(re.escape(data_item['date']), '__________', sentence)

    # ── FONCTIONS : cacher ce qui vient après le marqueur (la fonction) ──
    if pat_type == 'fonction':
        for marker in _FONCTION_MARKERS:
            m = re.search(rf"({marker})\s+(.+)", sentence, re.IGNORECASE)
            if m:
                before = sentence[:m.start(2)]
                after_text = m.group(2)
                # Garder la ponctuation finale
                punct = ''
                if after_text and after_text[-1] in '.,:;!':
                    punct = after_text[-1]
                return before + '__________' + punct
        # Fallback
        return _make_definition_trous(sentence, keyword)

    # ── EXEMPLES : cacher les exemples listés après le marqueur ──
    if pat_type == 'exemple':
        for marker in _EXEMPLE_MARKERS:
            m = re.search(rf"({marker})\s+(.+)", sentence, re.IGNORECASE)
            if m:
                before = sentence[:m.start(2)]
                return before + '__________'
        return _make_definition_trous(sentence, keyword)

    # ── TOUS LES AUTRES : cacher le mot-clé (sujet) ──
    return _make_definition_trous(sentence, keyword)


def is_definition_section(title: str) -> bool:
    """Vérifie si le titre de section indique un bloc de définitions."""
    t = title.lower().strip()
    return any(re.search(p, t) for p in _TITLE_DEF_MARKERS)


# ══════════════════════════════════════════════════════════════
#  PATTERN 2 — CAUSES / ORIGINES
# ══════════════════════════════════════════════════════════════

_CAUSE_MARKERS = [
    r"(?:a\s+été|est)\s+causée?\s+par",
    r"est\s+(?:dû|due)\s+à",
    r"résulte\s+de",
    r"s[''']explique\s+par",
    r"provient\s+de",
    r"est\s+provoquée?\s+par",
    r"trouve\s+(?:son|ses)\s+origines?\s+dans",
    r"est\s+liée?\s+à",
    r"a\s+(?:pour|comme)\s+(?:cause|origine|source)",
    r"est\s+(?:engendrée?|occasionnée?)\s+par",
    r"découle\s+de",
    r"tire\s+(?:son|ses)\s+origines?\s+de",
    r"en\s+raison\s+de",
]

_TITLE_CAUSE_MARKERS = [
    r"causes?", r"origines?", r"facteurs?", r"raisons?",
    r"sources?", r"pourquoi",
]


def detect_causes(text: str) -> list[dict]:
    """Détecte les patterns cause/origine. Retourne [{keyword, question, sentence}]."""
    sentences = re.split(r'[.!?\n;]+', text)
    results = []
    seen = set()
    for s in sentences:
        s = s.strip()
        if len(s) < 15:
            continue
        for marker in _CAUSE_MARKERS:
            pattern = rf"({_ART}.+?)\s+{marker}"
            m = re.search(pattern, s, re.IGNORECASE)
            if m:
                kw = _clean_keyword(m.group(1))
                if 1 <= len(kw.split()) <= 6 and kw.lower() not in seen:
                    seen.add(kw.lower())
                    results.append({
                        "keyword": kw,
                        "question": f"Quelles sont les causes de {kw.lower()} ?",
                        "sentence": s
                    })
                break
    return results


# ══════════════════════════════════════════════════════════════
#  PATTERN 3 — CONSÉQUENCES / EFFETS
# ══════════════════════════════════════════════════════════════

_CONSEQUENCE_MARKERS = [
    r"entraîne",
    r"provoque",
    r"conduit\s+à",
    r"a\s+pour\s+(?:effet|conséquence|résultat|impact)",
    r"aboutit\s+à",
    r"engendre",
    r"génère",
    r"produit",
    r"mène\s+à",
    r"cause\b",
    r"occasionne",
    r"(?:peut|risque\s+de)\s+(?:entraîner|provoquer|causer)",
    r"se\s+traduit\s+par",
    r"a\s+(?:un|des)\s+(?:effets?|impacts?|conséquences?)",
    r"est\s+(?:à\s+l[''']origine|responsable)\s+de",
]

_TITLE_CONSEQUENCE_MARKERS = [
    r"conséquences?", r"effets?", r"impacts?", r"résultats?",
    r"répercussions?", r"implications?",
]


def detect_consequences(text: str) -> list[dict]:
    """Détecte les patterns conséquence/effet. Retourne [{keyword, question, sentence}]."""
    sentences = re.split(r'[.!?\n;]+', text)
    results = []
    seen = set()
    for s in sentences:
        s = s.strip()
        if len(s) < 15:
            continue
        for marker in _CONSEQUENCE_MARKERS:
            pattern = rf"({_ART}.+?)\s+{marker}"
            m = re.search(pattern, s, re.IGNORECASE)
            if m:
                kw = _clean_keyword(m.group(1))
                if 1 <= len(kw.split()) <= 6 and kw.lower() not in seen:
                    seen.add(kw.lower())
                    results.append({
                        "keyword": kw,
                        "question": f"Quelles sont les conséquences de {kw.lower()} ?",
                        "sentence": s
                    })
                break
    return results


# ══════════════════════════════════════════════════════════════
#  PATTERN 4 — ÉTAPES / PROCESSUS / PHASES
# ══════════════════════════════════════════════════════════════

_ETAPE_MARKERS = [
    r"se\s+déroule\s+en",
    r"comporte\s+(?:\d+|plusieurs|différentes)\s+(?:étapes?|phases?)",
    r"comprend\s+(?:\d+|plusieurs)\s+(?:étapes?|phases?)",
    r"se\s+compose\s+de\s+(?:\d+|plusieurs)\s+(?:étapes?|phases?)",
    r"passe\s+par\s+(?:\d+|plusieurs)\s+(?:étapes?|phases?)",
    r"suit\s+(?:\d+|plusieurs)\s+(?:étapes?|phases?)",
]

_STEP_SEQUENCE_MARKERS = [
    r"d[''']abord", r"premièrement", r"en\s+premier\s+lieu",
    r"ensuite", r"deuxièmement", r"en\s+second\s+lieu", r"puis",
    r"troisièmement", r"après",
    r"enfin", r"finalement", r"en\s+dernier\s+lieu", r"pour\s+finir",
    r"étape\s+\d", r"phase\s+\d", r"\d\)\s*",
]

_TITLE_ETAPE_MARKERS = [
    r"étapes?", r"processus", r"phases?", r"déroulement",
    r"procédure", r"mécanisme", r"cycle", r"méthode",
]


def detect_etapes(text: str) -> list[dict]:
    """Détecte les patterns étape/processus. Retourne [{keyword, question, sentence, steps}]."""
    sentences = re.split(r'[.!?\n;]+', text)
    results = []
    seen = set()

    for s in sentences:
        s = s.strip()
        if len(s) < 20:
            continue
        for marker in _ETAPE_MARKERS:
            m = re.search(rf"({_ART}.+?)\s+{marker}", s, re.IGNORECASE)
            if m:
                kw = _clean_keyword(m.group(1))
                if 1 <= len(kw.split()) <= 6 and kw.lower() not in seen:
                    seen.add(kw.lower())
                    # Extraire les étapes listées après ":"
                    steps = []
                    after_colon = re.split(r'[:\-]', s, maxsplit=1)
                    if len(after_colon) > 1:
                        parts = re.split(r',\s*(?:puis|ensuite|et|enfin)?\s*', after_colon[1])
                        steps = [p.strip().rstrip('.').strip() for p in parts if len(p.strip()) > 2]
                    results.append({
                        "keyword": kw,
                        "question": f"Quelles sont les étapes de {kw.lower()} ?",
                        "sentence": s,
                        "steps": steps
                    })
                break

    # Aussi détecter les séquences d'abord/ensuite/enfin sans marqueur explicite
    if not results:
        seq_count = sum(1 for m in _STEP_SEQUENCE_MARKERS if re.search(m, text, re.IGNORECASE))
        if seq_count >= 2:
            results.append({
                "keyword": "ce processus",
                "question": "Quelles sont les étapes de ce processus ?",
                "sentence": text[:200],
                "steps": []
            })

    return results


# ══════════════════════════════════════════════════════════════
#  PATTERN 6 — CARACTÉRISTIQUES / PROPRIÉTÉS
# ══════════════════════════════════════════════════════════════

_CARACT_MARKERS = [
    r"se\s+caractérise\s+par",
    r"est\s+caractérisée?\s+par",
    r"possède",
    r"présente\s+(?:les?|des|plusieurs)",
    r"a\s+pour\s+(?:propriété|caractéristique|attribut|trait)",
    r"comporte",
    r"dispose\s+de",
    r"est\s+dotée?\s+de",
    r"se\s+distingue\s+par",
    r"a\s+(?:les?|des|plusieurs)\s+(?:caractéristiques?|propriétés?|traits?)",
]


def detect_caracteristiques(text: str) -> list[dict]:
    """Détecte les patterns caractéristique/propriété."""
    sentences = re.split(r'[.!?\n;]+', text)
    results, seen = [], set()
    for s in sentences:
        s = s.strip()
        if len(s) < 15: continue
        for marker in _CARACT_MARKERS:
            m = re.search(rf"({_ART}.+?)\s+{marker}", s, re.IGNORECASE)
            if m:
                kw = _clean_keyword(m.group(1))
                if 1 <= len(kw.split()) <= 6 and kw.lower() not in seen:
                    seen.add(kw.lower())
                    results.append({"keyword": kw, "question": f"Quelles sont les caractéristiques de {kw.lower()} ?", "sentence": s})
                break
    return results


# ══════════════════════════════════════════════════════════════
#  PATTERN 7 — FONCTIONS / RÔLES
# ══════════════════════════════════════════════════════════════

_FONCTION_MARKERS = [
    r"sert\s+à",
    r"permet\s+de",
    r"a\s+pour\s+(?:fonction|rôle|but|mission|objectif)",
    r"joue\s+(?:le|un)\s+rôle\s+de",
    r"assure",
    r"vise\s+à",
    r"est\s+utilisée?\s+pour",
    r"est\s+destinée?\s+à",
    r"contribue\s+à",
    r"a\s+pour\s+vocation\s+de",
    r"est\s+chargée?\s+de",
    r"remplit\s+(?:la|une)\s+fonction",
]


def detect_fonctions(text: str) -> list[dict]:
    """Détecte les patterns fonction/rôle."""
    sentences = re.split(r'[.!?\n;]+', text)
    results, seen = [], set()
    for s in sentences:
        s = s.strip()
        if len(s) < 15: continue
        for marker in _FONCTION_MARKERS:
            m = re.search(rf"({_ART}.+?)\s+{marker}", s, re.IGNORECASE)
            if m:
                kw = _clean_keyword(m.group(1))
                if 1 <= len(kw.split()) <= 6 and kw.lower() not in seen:
                    seen.add(kw.lower())
                    results.append({"keyword": kw, "question": f"À quoi sert {kw.lower()} ?", "sentence": s})
                break
    return results


# ══════════════════════════════════════════════════════════════
#  PATTERN 8 — EXEMPLES / ILLUSTRATIONS
# ══════════════════════════════════════════════════════════════

_EXEMPLE_MARKERS = [
    r"par\s+exemple",
    r"comme\s+(?:par\s+exemple\s+)?",
    r"tels?\s+que",
    r"notamment",
    r"c[''']est\s+le\s+cas\s+de",
    r"on\s+peut\s+citer",
    r"(?:est\s+)?illustrée?\s+par",
    r"à\s+l[''']image\s+de",
    r"incluent?",
    r"parmi\s+(?:les|eux|elles)",
    r"citons",
]


def detect_exemples(text: str) -> list[dict]:
    """Détecte les patterns d'exemples/illustrations."""
    sentences = re.split(r'[.!?\n;]+', text)
    results, seen = [], set()
    for s in sentences:
        s = s.strip()
        if len(s) < 15: continue
        for marker in _EXEMPLE_MARKERS:
            m = re.search(rf"({_ART}.+?)\s+{marker}", s, re.IGNORECASE)
            if m:
                kw = _clean_keyword(m.group(1))
                if 1 <= len(kw.split()) <= 6 and kw.lower() not in seen:
                    seen.add(kw.lower())
                    results.append({"keyword": kw, "question": f"Citez des exemples de {kw.lower()}.", "sentence": s})
                break
    return results


# ══════════════════════════════════════════════════════════════
#  PATTERN 9 — DATES / ÉVÉNEMENTS HISTORIQUES
# ══════════════════════════════════════════════════════════════

_DATE_MARKERS = [
    r"en\s+(\d{4})",
    r"le\s+(\d{1,2}\s+\w+\s+\d{4})",
    r"au\s+((?:X{0,3}(?:IX|IV|V?I{0,3}))\s*[eè](?:me)?\s+siècle)",
    r"(?:a\s+eu\s+lieu|s[''']est\s+produit|a\s+(?:débuté|commencé))\s+(?:en|le)\s+(.+?)(?:\s+(?:avec|par|lors))",
    r"(?:lors|pendant|au\s+cours)\s+de",
    r"à\s+l[''']époque\s+de",
    r"date\s+de",
]


def detect_dates(text: str) -> list[dict]:
    """Détecte les dates et événements historiques."""
    sentences = re.split(r'[.!?\n;]+', text)
    results, seen = [], set()
    for s in sentences:
        s = s.strip()
        if len(s) < 15: continue
        # Chercher une date dans la phrase
        date_match = re.search(r'\b(\d{4})\b', s)
        if not date_match:
            date_match = re.search(r'(\d{1,2}\s+\w+\s+\d{4})', s)
        if date_match:
            date_str = date_match.group(1)
            # Extraire le sujet/événement (avant la date)
            before = s[:date_match.start()].strip()
            kw = _clean_keyword(before) if before else ''
            if 2 <= len(kw.split()) <= 8 and kw.lower() not in seen:
                seen.add(kw.lower())
                results.append({
                    "keyword": kw,
                    "question": f"En quelle année {kw.lower()} a-t-il eu lieu ?",
                    "sentence": s,
                    "date": date_str
                })
    return results


# ══════════════════════════════════════════════════════════════
#  PATTERN 10 — AVANTAGES / INCONVÉNIENTS
# ══════════════════════════════════════════════════════════════

_AVANTAGE_MARKERS = [
    r"l[''']avantage\s+(?:est|de)",
    r"le\s+point\s+fort",
    r"l[''']atout",
    r"le\s+bénéfice",
    r"l[''']intérêt\s+(?:est|de)",
    r"le\s+risque\s+(?:est|de)",
    r"l[''']inconvénient",
    r"le\s+point\s+faible",
    r"la\s+limite\s+(?:est|de)",
    r"le\s+(?:dés)?avantage",
    r"(?:cependant|néanmoins|toutefois|en\s+revanche|mais)",
]


def detect_avantages(text: str) -> list[dict]:
    """Détecte les patterns avantages/inconvénients."""
    sentences = re.split(r'[.!?\n;]+', text)
    results, seen = [], set()
    has_avantage = any(re.search(r"avantage|point\s+fort|atout|bénéfice|intérêt", s, re.IGNORECASE) for s in sentences)
    has_inconvenient = any(re.search(r"inconvénient|risque|limite|point\s+faible|cependant|néanmoins|toutefois|en\s+revanche", s, re.IGNORECASE) for s in sentences)

    if has_avantage or has_inconvenient:
        # Trouver le sujet principal (souvent dans la première phrase ou le titre)
        for s in sentences:
            s = s.strip()
            if len(s) < 10: continue
            for marker in _AVANTAGE_MARKERS:
                m = re.search(rf"(?:{marker})\s+(?:du|de\s+la|de\s+l[''']|des|de)\s+(.+?)(?:\s+est|\s*,|\s*:)", s, re.IGNORECASE)
                if m:
                    kw = _clean_keyword(m.group(1))
                    if 1 <= len(kw.split()) <= 6 and kw.lower() not in seen:
                        seen.add(kw.lower())
                        q = "Citez un avantage et un inconvénient" if (has_avantage and has_inconvenient) else "Quels sont les avantages" if has_avantage else "Quelles sont les limites"
                        results.append({"keyword": kw, "question": f"{q} de {kw.lower()} ?", "sentence": s})
                    break
            if results: break

    return results



# ══════════════════════════════════════════════════════════════
#  PATTERN 11 — CLASSIFICATIONS / TYPOLOGIES
# ══════════════════════════════════════════════════════════════

_CLASSIF_MARKERS = [
    r"il\s+existe\s+(?:\d+|plusieurs|\w+)\s+(?:types|catégories)",
    r"on\s+distingue",
    r"se\s+divise\s+en",
    r"se\s+répartit\s+en",
    r"peut\s+être\s+classée?\s+en",
    r"on\s+recense",
]

def detect_classifications(text: str) -> list[dict]:
    sentences = re.split(r'[.!?\n;]+', text)
    results, seen = [], set()
    for s in sentences:
        s = s.strip()
        if len(s) < 15: continue
        for marker in _CLASSIF_MARKERS:
            m = re.search(rf"(?:{marker})\s+(?:de\s+|d['''])?(.+?)(?:\s*:|\s+qui|\.+)", s, re.IGNORECASE)
            if not m:
                m = re.search(rf"({_ART}.+?)\s+(?:{marker})", s, re.IGNORECASE)
            if m:
                kw = _clean_keyword(m.group(1))
                if 1 <= len(kw.split()) <= 6 and kw.lower() not in seen:
                    seen.add(kw.lower())
                    results.append({"keyword": kw, "question": f"Quels sont les différents types de {kw.lower()} ?", "sentence": s})
                break
    return results


# ══════════════════════════════════════════════════════════════
#  PATTERN 12 — CONDITIONS / CRITÈRES
# ══════════════════════════════════════════════════════════════

_CONDITION_MARKERS = [
    r"à\s+condition(?:s)?\s+(?:que|de)",
    r"nécessite",
    r"requiert",
    r"implique",
    r"suppose",
    r"il\s+faut\s+(?:que|un|une|des)",
    r"est\s+nécessaire",
]

def detect_conditions(text: str) -> list[dict]:
    sentences = re.split(r'[.!?\n;]+', text)
    results, seen = [], set()
    for s in sentences:
        s = s.strip()
        if len(s) < 15: continue
        for marker in _CONDITION_MARKERS:
            m = re.search(rf"Pour\s+(?:que\s+)?(.+?)(?:,?\s+{marker}|,?\s+il\s+faut)", s, re.IGNORECASE)
            if not m:
                m = re.search(rf"({_ART}.+?)\s+{marker}", s, re.IGNORECASE)
            if m:
                kw = _clean_keyword(m.group(1))
                if 1 <= len(kw.split()) <= 6 and kw.lower() not in seen:
                    seen.add(kw.lower())
                    results.append({"keyword": kw, "question": f"Quelles sont les conditions pour {kw.lower()} ?", "sentence": s})
                break
    return results


# ══════════════════════════════════════════════════════════════
#  PATTERN 13 — ACTEURS / AUTEURS
# ══════════════════════════════════════════════════════════════

_ACTEUR_MARKERS = [
    r"selon\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)",
    r"d[''']après\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)",
    r"([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\s+a\s+(?:dit|écrit|proposé|découvert)",
    r"théorie\s+de\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)",
    r"travaux\s+de\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)",
    r"découverte?\s+par\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)",
]

def detect_acteurs(text: str) -> list[dict]:
    sentences = re.split(r'[.!?\n;]+', text)
    results, seen = [], set()
    for s in sentences:
        s = s.strip()
        if len(s) < 15: continue
        for marker in _ACTEUR_MARKERS:
            m = re.search(marker, s)
            if m:
                name = m.group(1).strip()
                if len(name) > 3 and name.lower() not in seen:
                    seen.add(name.lower())
                    concept = "ce concept"
                    if "découvert par" in s.lower() or "proposé" in s.lower():
                        c_match = re.search(rf"({_ART}.+?)\s+(?:a\s+été\s+|(?:est\s+))?(?:découvert|proposé)", s, re.IGNORECASE)
                        if c_match:
                            concept = _clean_keyword(c_match.group(1))
                    results.append({"keyword": name, "question": f"Qui a découvert / proposé {concept} ?", "sentence": s})
                break
    return results


# ══════════════════════════════════════════════════════════════
#  PATTERN 14 — FORMULES / THÉORÈMES
# ══════════════════════════════════════════════════════════════

_FORMULE_MARKERS = [
    r"se\s+calcule\s+par",
    r"s[''']exprime\s+par",
    r"la\s+formule\s+est",
    r"selon\s+la\s+loi\s+de",
    r"le\s+théorème\s+stipule",
    r"la\s+relation\s+est",
    r"est\s+donnée?\s+par",
]

def detect_formules(text: str) -> list[dict]:
    sentences = re.split(r'[.!?\n;]+', text)
    results, seen = [], set()
    for s in sentences:
        s = s.strip()
        if len(s) < 15: continue
        for marker in _FORMULE_MARKERS:
            m = re.search(rf"({_ART}.+?)\s+(?:{marker})", s, re.IGNORECASE)
            if m:
                kw = _clean_keyword(m.group(1))
                if 1 <= len(kw.split()) <= 6 and kw.lower() not in seen:
                    seen.add(kw.lower())
                    results.append({"keyword": kw, "question": f"Quelle est la formule / règle de {kw.lower()} ?", "sentence": s})
                break
    return results


# ══════════════════════════════════════════════════════════════
#  PATTERN 15 — CHIFFRES / STATISTIQUES
# ══════════════════════════════════════════════════════════════

_CHIFFRE_MARKERS = [
    r"représente\s+(\d+(?:[.,]\d+)?\s*(?:%|pourcents?))",
    r"atteint\s+(\d+(?:[.,]\d+)?)",
    r"mesure\s+(\d+(?:[.,]\d+)?)",
    r"compte\s+(\d+(?:[.,]\d+)?)",
]

def detect_chiffres(text: str) -> list[dict]:
    sentences = re.split(r'[.!?\n;]+', text)
    results, seen = [], set()
    for s in sentences:
        s = s.strip()
        if len(s) < 15: continue
        for marker in _CHIFFRE_MARKERS:
            m = re.search(rf"({_ART}.+?)\s+(?:{marker})", s, re.IGNORECASE)
            if not m:
                m = re.search(rf"{marker}\s+(?:de\s+)?(.+?)\b", s, re.IGNORECASE)
            if m:
                kw = _clean_keyword(m.group(1))
                if 1 <= len(kw.split()) <= 6 and kw.lower() not in seen:
                    seen.add(kw.lower())
                    results.append({"keyword": kw, "question": f"Quel chiffre/pourcentage correspond à {kw.lower()} ?", "sentence": s})
                break
    return results


# ══════════════════════════════════════════════════════════════
#  PATTERN 16 — LOCALISATION
# ══════════════════════════════════════════════════════════════

_LOC_MARKERS = [
    r"se\s+situe",
    r"se\s+trouve",
    r"est\s+localisée?",
    r"dans\s+le",
    r"au\s+(?:nord|sud|est|ouest)\s+de",
    r"s[''']étend\s+sur",
]

def detect_localisations(text: str) -> list[dict]:
    sentences = re.split(r'[.!?\n;]+', text)
    results, seen = [], set()
    for s in sentences:
        s = s.strip()
        if len(s) < 15: continue
        for marker in _LOC_MARKERS:
            m = re.search(rf"({_ART}.+?)\s+(?:{marker})", s, re.IGNORECASE)
            if m:
                kw = _clean_keyword(m.group(1))
                if 1 <= len(kw.split()) <= 6 and kw.lower() not in seen:
                    seen.add(kw.lower())
                    results.append({"keyword": kw, "question": f"Où se situe {kw.lower()} ?", "sentence": s})
                break
    return results


# ══════════════════════════════════════════════════════════════
#  PATTERN 17 — COMPOSITION / STRUCTURE
# ══════════════════════════════════════════════════════════════

_COMPO_MARKERS = [
    r"est\s+composée?\s+de",
    r"comprend",
    r"contient",
    r"se\s+compose\s+de",
    r"est\s+constituée?\s+de",
    r"inclut",
    r"regroupe",
    r"est\s+formée?\s+de",
]

def detect_compositions(text: str) -> list[dict]:
    sentences = re.split(r'[.!?\n;]+', text)
    results, seen = [], set()
    for s in sentences:
        s = s.strip()
        if len(s) < 15: continue
        for marker in _COMPO_MARKERS:
            m = re.search(rf"({_ART}.+?)\s+(?:{marker})", s, re.IGNORECASE)
            if m:
                kw = _clean_keyword(m.group(1))
                if 1 <= len(kw.split()) <= 6 and kw.lower() not in seen:
                    seen.add(kw.lower())
                    results.append({"keyword": kw, "question": f"De quoi est composé(e) {kw.lower()} ?", "sentence": s})
                break
    return results


# ══════════════════════════════════════════════════════════════
#  PATTERN 18 — SYNONYMES
# ══════════════════════════════════════════════════════════════

_SYN_MARKERS = [
    r"aussi\s+appelée?",
    r"également\s+nommée?",
    r"autrement\s+dit",
    r"c[''']est-à-dire",
    r"alias",
    r"synonyme\s+de",
]

def detect_synonymes(text: str) -> list[dict]:
    sentences = re.split(r'[.!?\n;]+', text)
    results, seen = [], set()
    for s in sentences:
        s = s.strip()
        if len(s) < 15: continue
        for marker in _SYN_MARKERS:
            m = re.search(rf"({_ART}.+?)[\s,]+(?:{marker})", s, re.IGNORECASE)
            if m:
                kw = _clean_keyword(m.group(1))
                if 1 <= len(kw.split()) <= 6 and kw.lower() not in seen:
                    seen.add(kw.lower())
                    results.append({"keyword": kw, "question": f"Quels sont les synonymes / autres termes pour {kw.lower()} ?", "sentence": s})
                break
    return results


# ══════════════════════════════════════════════════════════════
#  PATTERN 19 — EXCEPTIONS
# ══════════════════════════════════════════════════════════════

_EXCEPT_MARKERS = [
    r"sauf",
    r"excepté",
    r"à\s+l[''']exception\s+de",
    r"hormis",
    r"attention",
    r"ne\s+s[''']applique\s+pas\s+à",
    r"cas\s+particulier",
    r"il\s+faut\s+noter\s+que",
]

def detect_exceptions(text: str) -> list[dict]:
    sentences = re.split(r'[.!?\n;]+', text)
    results, seen = [], set()
    for s in sentences:
        s = s.strip()
        if len(s) < 15: continue
        for marker in _EXCEPT_MARKERS:
            if re.search(rf"\b{marker}\b", s, re.IGNORECASE):
                kw = "cette règle"
                m = re.search(rf"({_ART}.+?)\s+(?:_|sauf|excepté)", s, re.IGNORECASE)
                if m: kw = _clean_keyword(m.group(1))
                if kw.lower() not in seen:
                    seen.add(kw.lower())
                    results.append({"keyword": kw, "question": f"Quelle est l'exception concernant {kw.lower()} ?", "sentence": s})
                break
    return results


# ══════════════════════════════════════════════════════════════
#  PATTERN 20 — OBJECTIFS / FINALITÉS
# ══════════════════════════════════════════════════════════════

_OBJECTIF_MARKERS = [
    r"a\s+pour\s+objectif",
    r"vise\s+à",
    r"dans\s+le\s+but\s+de",
    r"afin\s+de",
    r"l[''']enjeu\s+est\s+de",
    r"cherche\s+à",
]

def detect_objectifs(text: str) -> list[dict]:
    sentences = re.split(r'[.!?\n;]+', text)
    results, seen = [], set()
    for s in sentences:
        s = s.strip()
        if len(s) < 15: continue
        for marker in _OBJECTIF_MARKERS:
            m = re.search(rf"({_ART}.+?)\s+(?:{marker})", s, re.IGNORECASE)
            if not m:
                m = re.search(rf"(?:{marker})\s+(.+?)(?:\s*,|\.+)", s, re.IGNORECASE)
                if m:
                    kw = "ce processus"
                    if kw.lower() not in seen:
                        seen.add(kw.lower())
                        results.append({"keyword": kw, "question": f"Quel est l'objectif de {kw.lower()} ?", "sentence": s})
                    break
            else:
                kw = _clean_keyword(m.group(1))
                if 1 <= len(kw.split()) <= 6 and kw.lower() not in seen:
                    seen.add(kw.lower())
                    results.append({"keyword": kw, "question": f"Quel est l'objectif de {kw.lower()} ?", "sentence": s})
                break
    return results


# ══════════════════════════════════════════════════════════════
#  PATTERN 21 — STRUCTURE / SYNTAXE
# ══════════════════════════════════════════════════════════════

_STRUCTURE_MARKERS = [
    r"se\s+présente\s+comme\s+suit",
    r"la\s+structure\s+de",
    r"la\s+syntaxe\s+(?:générale\s+)?de",
    r"s[''']écrit",
    r"se\s+déclare",
    r"se\s+formule",
]

def detect_structures(text: str) -> list[dict]:
    sentences = re.split(r'[.!?\n;]+', text)
    results, seen = [], set()
    for s in sentences:
        s = s.strip()
        if len(s) < 10: continue
        
        for marker in _STRUCTURE_MARKERS:
            # Pattern A: La syntaxe de [mot-clé] est...
            m = re.search(rf"(?:structure|syntaxe)\s+(?:générale\s+)?(?:de\s+la|d[''']une|de\s+l[''']|du|de)\s+(?:requête|boucle|fonction|instruction\s+)?([A-Z0-9_]+(?:\s+[A-Z0-9_]+)*|[a-zA-Z0-9_]+)\b", s, re.IGNORECASE)
            
            # Pattern B: [mot-clé] s'écrit / se déclare
            if not m:
                m = re.search(rf"([a-zA-Z0-9_]+(?:\s+[a-zA-Z0-9_]+)*)\s+(?:s[''']écrit|se\s+déclare(?:comme\s+suit)?)", s, re.IGNORECASE)
            
            if m:
                kw = _clean_keyword(m.group(1))
                if kw.lower() not in seen and len(kw) > 1:
                    seen.add(kw.lower())
                    results.append({"keyword": kw, "question": f"Quelle est la structure de la syntaxe de {kw} ?", "sentence": s})
                break
                
            elif re.search(rf"\b{marker}\b", s, re.IGNORECASE):
                kw = "cet élément"
                if kw.lower() not in seen:
                    seen.add(kw.lower())
                    results.append({"keyword": kw, "question": f"Quelle est la structure / syntaxe de {kw} ?", "sentence": s})
                break
    return results

# ══════════════════════════════════════════════════════════════
#  PATTERN 22 — ABRÉVIATIONS / SIGNIFICATIONS
# ══════════════════════════════════════════════════════════════
def detect_abreviations(text: str) -> list[dict]:
    sentences = re.split(r'[.!?\n;]+', text)
    results, seen = [], set()
    for s in sentences:
        s = s.strip()
        if len(s) < 10: continue
        
        # Cas 1: Acronyme suivi de parenthèses
        m = re.search(r'\b([A-Z0-9]{2,10})\s+\(([^()]{5,})\)', s)
        if m:
            kw = m.group(1).strip()
            if kw.lower() not in seen:
                seen.add(kw.lower())
                results.append({"keyword": kw, "question": f"Que signifie l'acronyme {kw} ?", "sentence": s})
            continue
            
        # Cas 2: ... signifie ... / est l'abréviation de
        for marker in [r'signifie', r'veut dire', r"est l[''']abréviation de", r"est l[''']acronyme de"]:
            m = re.search(rf"([A-Za-z0-9_]+)\s+{marker}", s, re.IGNORECASE)
            if m:
                kw = m.group(1).strip()
                if len(kw) >= 2 and kw.lower() not in seen:
                    seen.add(kw.lower())
                    results.append({"keyword": kw, "question": f"Que signifie {kw} ?", "sentence": s})
                break
    return results

# ══════════════════════════════════════════════════════════════
#  PATTERN 23 — TABLEAUX DE FORMATS / C
# ══════════════════════════════════════════════════════════════
def detect_tableaux(text: str) -> list[dict]:
    sentences = re.split(r'[\n;]+', text)
    results, seen = [], set()
    for s in sentences:
        s = s.strip()
        if len(s) < 4: continue
        
        m = re.search(r'(%[a-zA-Z])\s*(?:[|:→-]*\s*)([a-zA-Zéèàâêôûîïç_]+(?:\s+[a-zA-Zéèàâêôûîïç_]+)*)', s)
        if m:
            kw = m.group(1).strip()
            val = m.group(2).strip().lower()
            if "printf" in s or "scanf" in s: continue
            if kw.lower() not in seen:
                seen.add(kw.lower())
                results.append({"keyword": kw, "question": f"Quel format utilise-t-on pour afficher/lire un(e) : {val} ?", "sentence": s})
    return results

# ══════════════════════════════════════════════════════════════
#  PATTERN 24 — NOTES / REMARQUES
# ══════════════════════════════════════════════════════════════
def detect_remarques(text: str) -> list[dict]:
    sentences = re.split(r'[.!?\n;]+', text)
    results, seen = [], set()
    for s in sentences:
        s = s.strip()
        if len(s) < 15: continue
        
        m = re.search(r'\b(NB|N\.B|Remarque|Attention|Important|À noter)\s*[:.-]*\s*(.+)', s, re.IGNORECASE)
        if m:
            content = m.group(2).strip()
            kw_match = re.search(r'(?:le|la|les|un|une)\s+(?:symbole|mot|fonction|caractère|instruction)?\s*([a-zA-Z0-9_&%]+)', content, re.IGNORECASE)
            kw = kw_match.group(1) if kw_match else "cette règle"
            if kw.lower() not in seen:
                seen.add(kw.lower())
                results.append({"keyword": kw, "question": f"Quelle information importante (NB/Attention) concerne {kw} ?", "sentence": s})
    return results

# ══════════════════════════════════════════════════════════════
#  PATTERN 25 — TRADUCTIONS ALGO ↔ CODE
# ══════════════════════════════════════════════════════════════
def detect_traductions(text: str) -> list[dict]:
    sentences = re.split(r'[\n;]+', text)
    results, seen = [], set()
    for s in sentences:
        s = s.strip()
        if len(s) < 5: continue
        
        kw = None
        if re.search(r'\b(?:écrire|afficher)\b', s, re.IGNORECASE) and re.search(r'\b(?:printf|console\.log|print)\b', s, re.IGNORECASE):
            kw = "une instruction d'écriture (ex: AFFICHER/ECRIRE)"
        elif re.search(r'\b(?:lire|saisir)\b', s, re.IGNORECASE) and re.search(r'\b(?:scanf|input|prompt|cin)\b', s, re.IGNORECASE):
            kw = "une instruction de lecture (ex: LIRE)"
        elif re.search(r'(?:←|<--|prend la valeur).*(?:=)', s, re.IGNORECASE) or ("←" in s and "=" in s):
            kw = "une d'affectation (←)"
        elif re.search(r'\b(?:sqrt|racine)\b', s, re.IGNORECASE) and ('√' in s or 'racine' in s):
            kw = "la racine carrée"
            
        if kw and kw not in seen:
            seen.add(kw)
            results.append({"keyword": kw, "question": f"Comment traduit-on {kw} en langage code ?", "sentence": s})
    return results

def _detect_best_pattern(sec) -> tuple:
    """Essaie tous les patterns et retourne le premier détecté.
    Retourne (type, data) ou (None, [])."""
    text = f"{sec.title}. {sec.content}"
    for name, func in [
        ('definition', detect_definitions),
        ('cause', detect_causes),
        ('consequence', detect_consequences),
        ('etape', detect_etapes),
        ('caracteristique', detect_caracteristiques),
        ('fonction', detect_fonctions),
        ('exemple', detect_exemples),
        ('date', detect_dates),
        ('avantage', detect_avantages),
        ('classification', detect_classifications),
        ('condition', detect_conditions),
        ('acteur', detect_acteurs),
        ('formule', detect_formules),
        ('chiffre', detect_chiffres),
        ('localisation', detect_localisations),
        ('composition', detect_compositions),
        ('synonyme', detect_synonymes),
        ('exception', detect_exceptions),
        ('abreviation', detect_abreviations),
        ('tableau', detect_tableaux),
        ('remarque', detect_remarques),
        ('traduction', detect_traductions),
        ('objectif', detect_objectifs),
        ('structure', detect_structures),
    ]:
        data = func(text)
        if data:
            return (name, data)
    return (None, [])


# ══════════════════════════════════════════════════════════════
#  MOTEUR 3 — GÉNÉRATEUR D'EXERCICES
#  Section × Difficulté × Syntaxe → Exercice personnalisé
# ══════════════════════════════════════════════════════════════

async def generate_exercises(req: GenerationRequest) -> list[ExerciseOutput]:
    """Génère des exercices selon les paramètres du wizard."""
    out = []
    diffs = ['facile', 'moyen', 'difficile'] if req.difficulty == 'progressif' else [req.difficulty]

    is_algo = req.lang == 'algo'
    is_py   = req.lang == 'python'

    for sec in req.sections:
        key = f"{sec.title} {sec.content}".lower()
        is_pour    = bool(re.search(r'\bpour\b|boucle pour|\bfor\b|nb fois|nombre de fois', key))
        is_tantque = bool(re.search(r'tant que|tantque|while|répéter|jusqu\'à', key))
        is_if      = bool(re.search(r'\bsi\b|sinon|alternative|condition|\bif\b|\belse\b', key))

        prefix = f"{sec.num} — " if sec.num else ""

        for d in diffs:
            out.append(_make_exercise(sec, d, is_pour, is_tantque, is_if, is_algo, is_py, prefix, req.appro))

    return out


def _make_exercise(sec, level, is_pour, is_tantque, is_if, is_algo, is_py, prefix, appro) -> ExerciseOutput:
    """Fabrique un exercice selon le pattern détecté et le niveau."""

    # ── Détection unique du meilleur pattern ──
    pat_type, pat_data = _detect_best_pattern(sec)

    # ═══════════════════════════════════════
    #  NIVEAU FACILE — Questions de rappel
    # ═══════════════════════════════════════
    if level == 'facile':

        if pat_type and pat_data:
            items_html = '<br>'.join([f"{i+1}. {d['question']}" for i, d in enumerate(pat_data[:6])])
            type_labels = {
                'definition': 'les notions',
                'cause': 'les causes',
                'consequence': 'les conséquences',
                'etape': 'les étapes / processus',
                'caracteristique': 'les caractéristiques',
                'fonction': 'les fonctions / rôles',
                'exemple': 'les exemples',
                'date': 'les dates et événements',
                'avantage': 'les avantages et inconvénients',
                'classification': 'les classifications / catégories',
                'condition': 'les conditions / critères',
                'acteur': 'les acteurs / auteurs',
                'formule': 'les formules / lois',
                'chiffre': 'les chiffres / données',
                'localisation': 'les localisations',
                'composition': 'la composition / structure',
                'synonyme': 'les synonymes',
                'exception': 'les exceptions',
                'abreviation': 'les abréviations et acronymes',
                'tableau': 'les formats et correspondances',
                'remarque': 'les notes importantes',
                'traduction': 'les traductions algo-code',
                'objectif': 'les objectifs / buts',
                'structure': 'la syntaxe / structure',
            }
            return ExerciseOutput(
                level='facile',
                title=f"Questions de cours — {prefix}{sec.title}",
                body=f"<strong>Objectif :</strong> Vérifier la compréhension de {type_labels.get(pat_type, 'ce chapitre')}.<br><br>"
                     f"Répondez aux questions suivantes :<br><br>"
                     f"{items_html}",
                code=None
            )

        # ★ FALLBACK : Quiz de discrimination (original)
        if is_pour:
            items = ['Afficher les entiers de 1 à 50', 'Calculer la somme de 10 nombres saisis', 'Afficher la table de multiplication de 7']
        elif is_tantque:
            items = ["Demander un mot de passe jusqu'à ce qu'il soit correct", "Saisir des nombres tant qu'ils sont négatifs", 'Continuer tant que l\'utilisateur ne saisit pas "0"']
        else:
            items = ['Vérifier si un nombre est pair ou impair', 'Afficher "Admis" ou "Échec" selon une note', 'Allumer le chauffage si température < 18°C']

        lang_struct = 'POUR / TANT QUE / SI-SINON' if is_algo else 'for / while / if-else'
        items_html = '<br>'.join([f"{i+1}. {it}" for i, it in enumerate(items)])
        return ExerciseOutput(
            level='facile',
            title=f"Quiz de discrimination — {prefix}{sec.title}",
            body=f"<strong>Objectif :</strong> Identifier la bonne structure algorithmique.<br><br>"
                 f"Pour chaque situation, indiquer la structure à utiliser ({lang_struct}) :<br><br>"
                 f"{items_html}",
            code=None
        )

    # ═══════════════════════════════════════
    #  NIVEAU MOYEN — Texte à trous
    # ═══════════════════════════════════════
    if level == 'moyen':

        if pat_type and pat_data:
            trous_items = []
            for i, d in enumerate(pat_data[:5]):
                trou = _make_pattern_trous(d['sentence'], d['keyword'], pat_type, d)
                trous_items.append(f"{i+1}. {trou}")
            items_html = '<br><br>'.join(trous_items)

            type_titles = {
                'definition': 'Définitions à compléter',
                'cause': 'Causes à compléter',
                'consequence': 'Conséquences à compléter',
                'etape': 'Étapes à compléter',
                'caracteristique': 'Caractéristiques à compléter',
                'fonction': 'Fonctions à compléter',
                'exemple': 'Exemples à compléter',
                'date': 'Dates à compléter',
                'avantage': 'Avantages / Inconvénients à compléter',
                'classification': 'Classifications à compléter',
                'condition': 'Conditions à compléter',
                'acteur': 'Auteurs à retrouver',
                'formule': 'Formules à compléter',
                'chiffre': 'Données à compléter',
                'localisation': 'Localisations à compléter',
                'composition': 'Compositions à compléter',
                'synonyme': 'Synonymes à compléter',
                'exception': 'Exceptions à compléter',
                'abreviation': 'Acronymes à développer',
                'tableau': 'Formats à associer',
                'remarque': 'Remarques à mémoriser',
                'traduction': 'Traductions algorithme/code',
                'objectif': 'Objectifs à compléter',
                'structure': 'Structures à compléter',
            }
            type_consignes = {
                'definition': 'Retrouver les termes manquants dans les définitions.',
                'cause': 'Retrouver les phénomènes dont on décrit les causes.',
                'consequence': 'Retrouver les causes dont on décrit les conséquences.',
                'etape': 'Retrouver les éléments manquants dans la description du processus.',
                'caracteristique': 'Retrouver les caractéristiques manquantes.',
                'fonction': 'Retrouver les fonctions ou rôles manquants.',
                'exemple': 'Retrouver les exemples manquants.',
                'date': 'Retrouver les dates ou événements manquants.',
                'avantage': 'Retrouver les avantages ou inconvénients manquants.',
                'classification': 'Retrouver les catégories ou types manquants.',
                'condition': 'Retrouver les conditions ou prérequis manquants.',
                'acteur': 'Retrouver les auteurs ou acteurs manquants.',
                'formule': 'Retrouver les éléments manquants dans les formules.',
                'chiffre': 'Retrouver les données chiffrées manquantes.',
                'localisation': 'Retrouver les localisations manquantes.',
                'composition': 'Retrouver les éléments de composition manquants.',
                'synonyme': 'Retrouver les synonymes manquants.',
                'exception': 'Retrouver les exceptions manquantes.',
                'abreviation': 'Développer les acronymes.',
                'tableau': 'Complétez les données de formats manquants.',
                'remarque': 'Complétez les informations soulignées dans les NB.',
                'traduction': 'Remplacez par la bonne instruction en langage C (ou autre).',
                'objectif': 'Retrouver les objectifs manquants.',
                'structure': 'Retrouver les éléments de syntaxe manquants.',
            }
            return ExerciseOutput(
                level='moyen',
                title=f"{type_titles.get(pat_type, 'Texte à compléter')} — {prefix}{sec.title}",
                body=f"<strong>Objectif :</strong> {type_consignes.get(pat_type, 'Compléter le texte.')}<br><br>"
                     f"Complétez chaque phrase en remplaçant les <code>__________</code> par le bon terme :<br><br>"
                     f"{items_html}",
                code=None
            )

        # ★ FALLBACK : Texte à trous code (original)
        if is_pour:
            if is_algo:
                code = "Variable i, somme : Entier\nDébut\n   somme ← 0\n   Pour i de __ à __ Faire\n      somme ← somme + i\n   FinPour\n   Écrire(\"Total : \", somme)\nFin"
            elif is_py:
                code = 'somme = 0\nfor i in range(__, __):\n    somme += __\nprint("Total :", somme)'
            else:
                code = 'let somme = 0;\nfor (let i = __; i <= __; i++) {\n    somme += i;\n}\nconsole.log("Total :", somme);'
        elif is_tantque:
            if is_algo:
                code = 'Variable n : Entier\nDébut\n   __________\n      Écrire("Entrez un nombre positif :")\n      Lire(n)\n   __________ (n > 0)\nFin'
            elif is_py:
                code = 'n = -1\n__________:\n    n = int(input("Nombre positif : "))\n    if n <= 0:\n        print("Invalide !")'
            else:
                code = 'let n;\n__________ {\n    n = parseInt(prompt("Nombre positif :"));\n} while (__________);'
        else:
            if is_algo:
                code = 'Variable note : Réel\nDébut\n   Lire(note)\n   Si __________ Alors\n      Écrire("Admis")\n   __________\n      Écrire("Échec")\n   FinSi\nFin'
            elif is_py:
                code = 'note = float(input("Note : "))\nif __________:\n    print("Admis")\n__________:\n    print("Échec")'
            else:
                code = 'let note = parseFloat(prompt("Note :"));\nif (__________) {\n    console.log("Admis");\n} __________ {\n    console.log("Échec");\n}'

        return ExerciseOutput(
            level='moyen',
            title=f"Texte à trous — {prefix}{sec.title}",
            body=f"<strong>Objectif :</strong> Compléter la syntaxe manquante.<br><br>"
                 f"Complétez les <code>__________</code> pour que l'algorithme fonctionne correctement :",
            code=code
        )

    # ═══════════════════════════════════════
    #  NIVEAU DIFFICILE — Production libre
    # ═══════════════════════════════════════

    if pat_type and pat_data:
        keywords_list = [d['keyword'] for d in pat_data[:6]]
        items_html = '<br>'.join([f"{i+1}. <strong>{kw}</strong>" for i, kw in enumerate(keywords_list)])

        type_titles = {
            'definition': 'Rédaction de définitions',
            'cause': 'Analyse des causes',
            'consequence': 'Analyse des conséquences',
            'etape': 'Restitution des étapes',
            'caracteristique': 'Description des caractéristiques',
            'fonction': 'Explication des fonctions',
            'exemple': 'Production d\'exemples',
            'date': 'Restitution chronologique',
            'avantage': 'Argumentation pour/contre',
            'classification': 'Restitution des catégories',
            'condition': 'Explication des conditions',
            'acteur': 'Identification des auteurs',
            'formule': 'Restitution des formules',
            'chiffre': 'Analyse des données',
            'localisation': 'Description géographique',
            'composition': 'Description de structure',
            'synonyme': 'Recherche de synonymes',
            'exception': 'Analyse des cas particuliers',
            'abreviation': 'Explication des Acronymes',
            'tableau': 'Restitution des correspondances',
            'remarque': 'Analyse des règles spécifiques',
            'traduction': 'Traduction Algorithmique',
            'objectif': 'Explication des finalités',
            'structure': 'Production de syntaxe',
        }
        type_consignes = {
            'definition': 'Rédigez les définitions de mémoire, avec vos propres mots.',
            'cause': 'Expliquez les causes des phénomènes suivants, de mémoire.',
            'consequence': 'Décrivez les conséquences des phénomènes suivants, de mémoire.',
            'etape': 'Décrivez dans l\'ordre les étapes des processus suivants.',
            'caracteristique': 'Décrivez les caractéristiques des éléments suivants.',
            'fonction': 'Expliquez le rôle et la fonction de chaque élément.',
            'exemple': 'Donnez au moins 3 exemples pour chaque concept.',
            'date': 'Situez chaque événement dans le temps et expliquez son contexte.',
            'avantage': 'Présentez les avantages ET les inconvénients de chaque sujet.',
            'classification': 'Citez les différentes catégories ou types pour chaque sujet.',
            'condition': 'Décrivez les conditions nécessaires pour chaque point.',
            'acteur': 'Identifiez et décrivez l\'importance de chaque auteur/acteur.',
            'formule': 'Explicitez la formule ou le théorème et expliquez chaque terme.',
            'chiffre': 'Rappelez les données clés et expliquez leur signification.',
            'localisation': 'Situez précisément chaque élément.',
            'composition': 'Décrivez la structure et la composition de chaque élément.',
            'synonyme': 'Donnez des synonymes pertinents et expliquez les nuances.',
            'exception': 'Expliquez l\'exception et la règle générale qui s\'y rattache.',
            'abreviation': 'Donnez la signification complète de chaque acronyme.',
            'tableau': 'Détaillez à quel type/valeur correspond chaque élément.',
            'remarque': 'Détaillez de mémoire les notes ou remarques spécifiques sur :',
            'traduction': 'Traduisez ou donnez l\'équivalent logique / code pour :',
            'objectif': 'Explicitez les objectifs et les enjeux de chaque sujet.',
            'structure': 'Donnez la structure ou syntaxe générale de l\'élément suivant.',
        }
        type_verbes = {
            'definition': 'Définissez chacun des termes suivants :',
            'cause': 'Citez et expliquez les causes de :',
            'consequence': 'Citez et expliquez les conséquences de :',
            'etape': 'Décrivez dans l\'ordre les étapes de :',
            'caracteristique': 'Décrivez les caractéristiques de :',
            'fonction': 'Expliquez à quoi sert :',
            'exemple': 'Donnez des exemples concrets de :',
            'date': 'Datez et expliquez les événements suivants :',
            'avantage': 'Argumentez pour et contre :',
            'classification': 'Listez les types de :',
            'condition': 'Quelles sont les conditions pour :',
            'acteur': 'Présentez la contribution de :',
            'formule': 'Donnez la formule / le théorème de :',
            'chiffre': 'Donnez les chiffres clés sur :',
            'localisation': 'Où situe-t-on :',
            'composition': 'De quoi est composé :',
            'synonyme': 'Quels sont les autres termes pour :',
            'exception': 'Quelle est l\'exception pour :',
            'abreviation': 'À quoi correspond l\'acronyme :',
            'tableau': 'Donnez la ou les correspondances pour :',
            'remarque': 'Rappelez les consignes (NB/Attention) pour :',
            'traduction': 'Écrivez l\'équivalent code ou algorithme de :',
            'objectif': 'Quels sont les objectifs de :',
            'structure': 'Quelle est la syntaxe de :'
        }

        return ExerciseOutput(
            level='difficile',
            title=f"{type_titles.get(pat_type, 'Production libre')} — {prefix}{sec.title}",
            body=f"<strong>Objectif :</strong> {type_consignes.get(pat_type, 'Production autonome.')}<br><br>"
                 f"{type_verbes.get(pat_type, 'Répondez :')}<br><br>"
                 f"{items_html}<br><br>"
                 f"<em>Conseil : soyez précis et donnez des exemples concrets.</em>",
            code=None
        )

    # ★ FALLBACK : Production autonome (original)
    if appro:
        challenge = (
            "Écrivez un programme complet qui :<br><br>"
            "1. Demande le prix de <strong>5 articles</strong> l'un après l'autre avec une boucle<br>"
            "2. Calcule le total et applique une <strong>remise de 10%</strong> si total > 100 000 FCFA<br>"
            "3. Affiche le montant avec et sans remise<br>"
            "<em>Bonus : forcez l'utilisateur à saisir un prix valide (> 0)</em>"
        )
    else:
        challenge = (
            "Écrivez un algorithme qui :<br><br>"
            "1. Demande à l'élève de saisir sa note sur 20<br>"
            '2. Affiche <strong>"Admis"</strong> si note ≥ 10, <strong>"Échec"</strong> sinon<br>'
            "3. Utilise une boucle pour forcer une saisie valide (0 à 20)"
        )

    return ExerciseOutput(
        level='difficile',
        title=f"{'Défi Expert' if appro else 'Mini-Projet'} — {prefix}{sec.title}",
        body=f"<strong>Objectif :</strong> Production algorithmique autonome.<br><br>{challenge}",
        code=None
    )


# ══════════════════════════════════════════════════════════════
#  MOTEUR 4 — APPROFONDISSEMENT (Bouton "Approfondir")
#  Génère une version augmentée d'un exercice spécifique
#  avec code adapté à la syntaxe détectée
# ══════════════════════════════════════════════════════════════

async def deepen_exercise(req: DeepenRequest) -> ExerciseOutput:
    """Génère une version approfondie d'un exercice donné, dans la bonne syntaxe."""
    is_algo = req.lang == 'algo'
    is_py   = req.lang == 'python'

    body = (
        "<strong>Défi Expert :</strong> Reprenez l'exercice et ajoutez :<br><br>"
        "1. Gestion des <strong>cas d'erreur</strong> (saisie invalide, valeur hors limite)<br>"
        "2. Un <strong>compteur de tentatives</strong> affiché à la fin<br>"
        "3. Une <strong>validation en boucle</strong> jusqu'à saisie correcte<br>"
        "<em>Bonus : combiner avec une alternative pour afficher un résultat différent selon le score</em>"
    )

    if is_algo:
        code = (
            "Variable n, tentatives : Entier\n"
            "Début\n"
            "   tentatives ← 0\n"
            "   Répéter\n"
            '      Écrire("Saisir une valeur valide :")\n'
            "      Lire(n)\n"
            "      tentatives ← tentatives + 1\n"
            "      Si (n < 0 OU n > 100) Alors\n"
            '         Écrire("Erreur ! Valeur hors limites.")\n'
            "      FinSi\n"
            "   Jusqu'à (n >= 0 ET n <= 100)\n"
            '   Écrire("Nb tentatives : ", tentatives)\n'
            "Fin"
        )
    elif is_py:
        code = (
            "tentatives = 0\n"
            "while True:\n"
            "    try:\n"
            '        n = int(input("Saisir une valeur (0-100) : "))\n'
            "        if 0 <= n <= 100:\n"
            "            break\n"
            '        print("Valeur hors limites !")\n'
            "    except ValueError:\n"
            '        print("Saisie invalide !")\n'
            "    tentatives += 1\n"
            'print(f"Tentatives : {tentatives}")'
        )
    else:
        code = (
            "let n, tentatives = 0;\n"
            "do {\n"
            '  n = parseInt(prompt("Valeur (0-100) :"));\n'
            '  if (isNaN(n)) console.log("Invalide !");\n'
            '  else if (n<0||n>100) console.log("Hors limites !");\n'
            "  tentatives++;\n"
            "} while (isNaN(n) || n<0 || n>100);\n"
            'console.log("Tentatives :", tentatives);'
        )

    return ExerciseOutput(
        level='difficile',
        title=f"▲ Version Approfondie — {req.exerciseTitle}",
        body=body,
        code=code
    )
