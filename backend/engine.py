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
    # Retirer mots parasites fréquents en début
    kw = re.sub(r"^(?:autre|autres|principal|principale|seul|seule|même|premier|première)\s+", '', kw, flags=re.IGNORECASE)
    # Tronquer si trop long (garder max 5 mots)
    words = kw.split()
    if len(words) > 5:
        kw = ' '.join(words[:5])
    return kw.strip()


def _build_question(keyword: str, sentence: str) -> str:
    """Formule 'Qu'est-ce que/qu'un/une [keyword] ?' avec le bon article."""
    s_low = sentence.lower()
    kw_low = keyword.lower()
    first = kw_low[0] if kw_low else ''
    vowel = first in 'aeéèêëiïîoôuùûyh'

    # Détecter le genre depuis la phrase source
    if re.search(rf'\bune\s+{re.escape(kw_low)}', s_low):
        article = "une "
    elif re.search(rf"\bl['']{re.escape(kw_low)}", s_low) or vowel:
        article = "l'" if vowel else "le "
    else:
        article = "la " if re.search(rf'\bla\s+{re.escape(kw_low)}', s_low) else "un "

    if article in ("l'", "l'"):
        return f"Qu'est-ce que l'{keyword} ?"
    return f"Qu'est-ce que {article}{keyword} ?"


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
            pattern = rf"({_ART}[\w''éèêëàâùûîïôœç]+(?:\s+[\w''éèêëàâùûîïôœç]+){{0,3}})\s+{marker}"
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
            pattern = rf"({_ART}[\w''éèêëàâùûîïôœç]+(?:\s+[\w''éèêëàâùûîïôœç]+){0,3})\s+{marker}"
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
            pattern = rf"({_ART}[\w''éèêëàâùûîïôœç]+(?:\s+[\w''éèêëàâùûîïôœç]+){0,3})\s+{marker}"
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
            m = re.search(rf"({_ART}[\w''éèêëàâùûîïôœç]+(?:\s+[\w''éèêëàâùûîïôœç]+){0,3})\s+{marker}", s, re.IGNORECASE)
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
            m = re.search(rf"({_ART}[\w''éèêëàâùûîïôœç]+(?:\s+[\w''éèêëàâùûîïôœç]+){0,3})\s+{marker}", s, re.IGNORECASE)
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
            m = re.search(rf"({_ART}[\w''éèêëàâùûîïôœç]+(?:\s+[\w''éèêëàâùûîïôœç]+){0,3})\s+{marker}", s, re.IGNORECASE)
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
            m = re.search(rf"({_ART}[\w''éèêëàâùûîïôœç]+(?:\s+[\w''éèêëàâùûîïôœç]+){0,3})\s+{marker}", s, re.IGNORECASE)
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
                m = re.search(rf"({_ART}[\w''éèêëàâùûîïôœç]+(?:\s+[\w''éèêëàâùûîïôœç]+){0,3})\s+(?:{marker})", s, re.IGNORECASE)
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
                m = re.search(rf"({_ART}[\w''éèêëàâùûîïôœç]+(?:\s+[\w''éèêëàâùûîïôœç]+){0,3})\s+{marker}", s, re.IGNORECASE)
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
                        c_match = re.search(rf"({_ART}[\w''éèêëàâùûîïôœç]+(?:\s+[\w''éèêëàâùûîïôœç]+){0,3})\s+(?:a\s+été\s+|(?:est\s+))?(?:découvert|proposé)", s, re.IGNORECASE)
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
            m = re.search(rf"({_ART}[\w''éèêëàâùûîïôœç]+(?:\s+[\w''éèêëàâùûîïôœç]+){0,3})\s+(?:{marker})", s, re.IGNORECASE)
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
            m = re.search(rf"({_ART}[\w''éèêëàâùûîïôœç]+(?:\s+[\w''éèêëàâùûîïôœç]+){0,3})\s+(?:{marker})", s, re.IGNORECASE)
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
            m = re.search(rf"({_ART}[\w''éèêëàâùûîïôœç]+(?:\s+[\w''éèêëàâùûîïôœç]+){0,3})\s+(?:{marker})", s, re.IGNORECASE)
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
            m = re.search(rf"({_ART}[\w''éèêëàâùûîïôœç]+(?:\s+[\w''éèêëàâùûîïôœç]+){0,3})\s+(?:{marker})", s, re.IGNORECASE)
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
                m = re.search(rf"({_ART}[\w''éèêëàâùûîïôœç]+(?:\s+[\w''éèêëàâùûîïôœç]+){0,3})\s+(?:_|sauf|excepté)", s, re.IGNORECASE)
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
            m = re.search(rf"({_ART}[\w''éèêëàâùûîïôœç]+(?:\s+[\w''éèêëàâùûîïôœç]+){0,3})\s+(?:{marker})", s, re.IGNORECASE)
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

# ══════════════════════════════════════════════════════════════
#  PATTERNS 26-31 — DÉTECTION DE BLOCS DE SYNTAXE
#  Priorité maximale : priment sur tous les autres patterns
# ══════════════════════════════════════════════════════════════

def detect_syntaxe_pour(text: str) -> list[dict]:
    """Détecte un bloc de boucle POUR / for dans le texte."""
    patterns = [
        r'POUR\s+\w+\s+DE\s+.+\s+(?:À|A)\s+.+\s+FAIRE',
        r'for\s+\w+\s+in\s+range\s*\(',
        r'for\s*\(let\s+\w+\s*=',
        r'for\s*\(int\s+\w+\s*=',
        r'for\s*\(var\s+\w+\s*=',
        r'FIN\s+POUR',
    ]
    for p in patterns:
        if re.search(p, text, re.IGNORECASE):
            return [{"keyword": "boucle POUR", "question": "Écrire un algorithme utilisant une boucle POUR", "sentence": text[:200]}]
    title_low = text.split('.')[0].lower()
    if re.search(r'boucle\s+pour|boucle\s+for|répétition\s+fixe|compteur|nombre\s+de\s+fois', title_low):
        return [{"keyword": "boucle POUR", "question": "Écrire un algorithme utilisant une boucle POUR", "sentence": text[:200]}]
    return []


def detect_syntaxe_tantque(text: str) -> list[dict]:
    """Détecte un bloc TANT QUE / while dans le texte."""
    patterns = [
        r'TANT\s+QUE\s+.+\s+FAIRE',
        r'FIN\s+TANT\s+QUE',
        r'while\s+\w+.*:',
        r'while\s*\(.+\)\s*\{',
    ]
    for p in patterns:
        if re.search(p, text, re.IGNORECASE):
            return [{"keyword": "boucle TANT QUE", "question": "Écrire un algorithme utilisant une boucle TANT QUE", "sentence": text[:200]}]
    title_low = text.split('.')[0].lower()
    if re.search(r'tant\s+que|while|boucle\s+condition|répétition\s+condition', title_low):
        return [{"keyword": "boucle TANT QUE", "question": "Écrire un algorithme utilisant une boucle TANT QUE", "sentence": text[:200]}]
    return []


def detect_syntaxe_repeter(text: str) -> list[dict]:
    """Détecte un bloc RÉPÉTER JUSQU'À / do-while dans le texte."""
    patterns = [
        r"RÉPÉTER",
        r"JUSQU[''']À",
        r'do\s*\{',
        r'\}\s*while\s*\(',
    ]
    matched = sum(1 for p in patterns if re.search(p, text, re.IGNORECASE))
    if matched >= 1:
        title_low = text.split('.')[0].lower()
        if re.search(r"répéter|jusqu[''']à|do.while|post.condition|saisie\s+valid", title_low) or matched >= 2:
            return [{"keyword": "boucle RÉPÉTER JUSQU'À", "question": "Écrire un algorithme utilisant une boucle RÉPÉTER JUSQU'À", "sentence": text[:200]}]
    return []


def detect_syntaxe_si(text: str) -> list[dict]:
    """Détecte un bloc SI/SINON / if-else dans le texte."""
    patterns = [
        r'SI\s+.+\s+ALORS',
        r'FIN\s+SI',
        r'SINON\s+SI',
        r'if\s+.+:',
        r'elif\s+',
        r'if\s*\(.+\)\s*\{',
        r'else\s+if\s*\(',
    ]
    for p in patterns:
        if re.search(p, text, re.IGNORECASE):
            return [{"keyword": "structure SI/SINON", "question": "Écrire un algorithme utilisant une alternative SI/SINON", "sentence": text[:200]}]
    title_low = text.split('.')[0].lower()
    if re.search(r'alternative|si\s+sinon|if\s+else|structure\s+conditionnelle|prise\s+de\s+décision', title_low):
        return [{"keyword": "structure SI/SINON", "question": "Écrire un algorithme utilisant une alternative SI/SINON", "sentence": text[:200]}]
    return []


def detect_syntaxe_fonction(text: str) -> list[dict]:
    """Détecte une déclaration de fonction / procédure dans le texte."""
    patterns = [
        r'FONCTION\s+\w+\s*\(',
        r'PROCÉDURE\s+\w+\s*\(',
        r'PROCEDURE\s+\w+\s*\(',
        r'RETOURNER\s+',
        r'def\s+\w+\s*\(',
        r'function\s+\w+\s*\(',
    ]
    for p in patterns:
        if re.search(p, text, re.IGNORECASE):
            return [{"keyword": "fonction/procédure", "question": "Écrire et appeler une fonction", "sentence": text[:200]}]
    title_low = text.split('.')[0].lower()
    if re.search(r'fonction|procédure|sous-programme|def |modularité|retourner', title_low):
        return [{"keyword": "fonction/procédure", "question": "Écrire et appeler une fonction", "sentence": text[:200]}]
    return []


def detect_syntaxe_tableau(text: str) -> list[dict]:
    """Détecte une déclaration ou utilisation de tableau / array dans le texte."""
    patterns = [
        r'TABLEAU\s*\[',
        r'\w+\s*\[\s*\d+\s*\.\.\s*\d*',
        r'\w+\s*\[\s*i\s*\]',
        r'\[\s*\]\s*\*\s*\d+',
        r'\.append\s*\(',
        r'\.push\s*\(',
        r'new\s+Array\s*\(',
    ]
    for p in patterns:
        if re.search(p, text, re.IGNORECASE):
            return [{"keyword": "tableau/liste", "question": "Écrire un algorithme utilisant un tableau", "sentence": text[:200]}]
    title_low = text.split('.')[0].lower()
    if re.search(r'\btableau\b|array|\bliste\b|indice|index|parcours\s+de', title_low):
        return [{"keyword": "tableau/liste", "question": "Écrire un algorithme utilisant un tableau", "sentence": text[:200]}]
    return []


# ══════════════════════════════════════════════════════════════
#  PATTERNS 32-40 — ANALYSE, COMPARAISON, RÈGLES
#  Priorité 2 : après syntaxe, avant patterns textuels classiques
# ══════════════════════════════════════════════════════════════

def detect_comparaison(text: str) -> list[dict]:
    markers = [
        r"contrairement\s+à",
        r"à\s+l[''']opposé\s+de",
        r"tandis\s+que",
        r"alors\s+que",
        r"par\s+opposition\s+à",
        r"en\s+revanche",
        r"différence\s+entre",
        r"comparé\s+à",
        r"par\s+rapport\s+à",
        r"\bvs\b|\bversus\b",
    ]
    for marker in markers:
        m = re.search(marker, text, re.IGNORECASE)
        if m:
            before = text[:m.start()].strip().split()[-5:]
            kw = ' '.join(before).strip('.,;:') or sec_title_from(text)
            return [{"keyword": _clean_keyword(kw), "question": f"Comparez les deux éléments mentionnés.", "sentence": text[:300]}]
    return []


def detect_erreur_piege(text: str) -> list[dict]:
    markers = [
        r"erreur\s+(?:courante|fréquente|typique|classique|commune|à\s+éviter)",
        r"piège\s+(?:fréquent|courant|classique)",
        r"attention\s+à\s+ne\s+pas",
        r"ne\s+pas\s+confondre",
        r"faute\s+(?:courante|fréquente|classique)",
        r"risque\s+d[''']erreur",
    ]
    for marker in markers:
        m = re.search(marker, text, re.IGNORECASE)
        if m:
            after = text[m.end():m.end()+80].strip().split('.')[0]
            kw = _clean_keyword(after[:40]) or "cette règle"
            return [{"keyword": kw, "question": f"Identifiez et corrigez l'erreur décrite.", "sentence": text[:300]}]
    return []


def detect_trace_execution(text: str) -> list[dict]:
    markers = [
        r"tableau\s+de\s+(?:trace|valeurs|suivi)",
        r"trace\s+d[''']exécution",
        r"déroulement\s+pas\s+à\s+pas",
        r"valeurs\s+successives",
        r"à\s+l[''']itération\s+\d",
        r"après\s+exécution",
        r"état\s+du\s+programme",
    ]
    for marker in markers:
        if re.search(marker, text, re.IGNORECASE):
            return [{"keyword": "trace d'exécution", "question": "Complétez le tableau de trace.", "sentence": text[:300]}]
    return []


def detect_entree_sortie(text: str) -> list[dict]:
    markers = [
        r"prend\s+en\s+entrée",
        r"retourne\s+(?:en\s+sortie|une\s+valeur|le\s+résultat)",
        r"données?\s+d[''']entrée",
        r"(?:valeur|résultat)\s+(?:de\s+retour|retourné)",
        r"paramètres?\s+d[''']entrée",
        r"entrée\s*:",
        r"sortie\s*:",
    ]
    for marker in markers:
        m = re.search(marker, text, re.IGNORECASE)
        if m:
            return [{"keyword": "interface de la fonction", "question": "Identifiez les entrées et sorties.", "sentence": text[:300]}]
    return []


def detect_preconditions(text: str) -> list[dict]:
    markers = [
        r"précondition",
        r"postcondition",
        r"à\s+condition\s+que",
        r"sous\s+réserve\s+que",
        r"garantit\s+que",
        r"assure\s+que",
        r"contrat\s+(?:de|d['''])",
    ]
    for marker in markers:
        m = re.search(marker, text, re.IGNORECASE)
        if m:
            return [{"keyword": "préconditions/postconditions", "question": "Énoncez les préconditions et postconditions.", "sentence": text[:300]}]
    return []


def detect_conversion_langage(text: str) -> list[dict]:
    has_algo = bool(re.search(r'POUR\s+\w+\s+DE|TANT\s+QUE|RÉPÉTER|FONCTION\s+\w+\s*\(|RETOURNER', text))
    has_py   = bool(re.search(r'\bdef\s+\w+\s*\(|\bfor\s+\w+\s+in\s+|\bwhile\s+', text))
    has_js   = bool(re.search(r'\bfunction\s+\w+\s*\(|console\.log\s*\(|\bconst\b|\blet\b', text))
    explicit = bool(re.search(
        r"équivalent\s+en\s+(?:Python|JavaScript|algorithmique)|s[''']écrit\s+en\s+Python"
        r"|se\s+traduit\s+en\s+(?:JavaScript|Python)|correspond\s+en\s+(?:Python|JavaScript)"
        r"|la\s+même\s+chose\s+en\s+(?:Python|JavaScript)",
        text, re.IGNORECASE))
    if explicit or (has_algo and (has_py or has_js)):
        return [{"keyword": "traduction langage", "question": "Traduisez dans l'autre langage.", "sentence": text[:300]}]
    return []


def detect_complexite(text: str) -> list[dict]:
    markers = [
        r"complexité\s+(?:en\s+temps|en\s+espace|temporelle|spatiale|algorithmique)?",
        r"O\s*\(\s*(?:n²?|n\^2|log\s*n|1|n\s*log\s*n)\s*\)",
        r"plus\s+(?:efficace|optimal|rapide)\s+que",
        r"moins\s+efficace",
        r"coût\s+(?:en\s+mémoire|computationnel|d[''']exécution)",
        r"nombre\s+d[''']opérations",
        r"algorithme\s+optimal",
    ]
    for marker in markers:
        m = re.search(marker, text, re.IGNORECASE)
        if m:
            return [{"keyword": "complexité algorithmique", "question": "Analysez la complexité et proposez une amélioration.", "sentence": text[:300]}]
    return []


def detect_regle_absolue(text: str) -> list[dict]:
    markers = [
        r"il\s+faut\s+toujours",
        r"on\s+ne\s+doit\s+(?:jamais|pas)",
        r"ne\s+jamais\s+",
        r"principe\s+fondamental",
        r"règle\s+(?:d[''']or|de\s+base|fondamentale)",
        r"toujours\s+(?:vérifier|s[''']assurer|initialiser)",
        r"interdit\s+de",
    ]
    for marker in markers:
        m = re.search(marker, text, re.IGNORECASE)
        if m:
            after = text[m.end():m.end()+80].strip().split('.')[0]
            kw = _clean_keyword(after[:40]) or "cette règle"
            return [{"keyword": kw, "question": "Énoncez la règle et donnez un contre-exemple.", "sentence": text[:300]}]
    return []


def detect_schema(text: str) -> list[dict]:
    markers = [
        r"(?:le|un)\s+schéma\s+(?:montre|représente|illustre)",
        r"comme\s+le\s+montre\s+(?:la\s+figure|le\s+diagramme|le\s+schéma)",
        r"représenté\s+par\s+(?:le|un)\s+(?:diagramme|schéma)",
        r"(?:la\s+figure|le\s+diagramme)\s+(?:ci-dessous|suivant)",
        r"représentation\s+graphique",
        r"\borganigramme\b",
        r"diagramme\s+(?:de|d[''']|des)",
    ]
    for marker in markers:
        if re.search(marker, text, re.IGNORECASE):
            return [{"keyword": "schéma/organigramme", "question": "Décrivez ou reproduisez le schéma.", "sentence": text[:300]}]
    return []


def sec_title_from(text: str) -> str:
    """Extrait le titre (première phrase) d'un texte pour fallback de mot-clé."""
    return text.split('.')[0][:40].strip()


def _make_analyse_exercise(sec, level, pat_type, is_algo, is_py, prefix) -> ExerciseOutput:
    """Génère un exercice d'analyse/comparaison pour les patterns 32-40."""

    title_sec = sec.title.strip()

    META = {
        'comparaison': {
            'nom': 'Comparaison',
            'facile_body': (
                f"<strong>Objectif :</strong> Comparer deux concepts de la section «&nbsp;{title_sec}&nbsp;».<br><br>"
                f"Répondez aux questions suivantes :<br><br>"
                f"1. Citez <strong>deux différences</strong> entre les éléments comparés dans le cours.<br>"
                f"2. Citez <strong>un point commun</strong> entre ces deux éléments.<br>"
                f"3. Dans quel cas choisiriez-vous l'un plutôt que l'autre ?"
            ),
            'moyen_body': (
                f"<strong>Objectif :</strong> Compléter le tableau comparatif.<br><br>"
                f"Remplissez chaque cellule vide :"
            ),
            'moyen_code': (
                f"Critère          | Élément A          | Élément B\n"
                f"─────────────────┼────────────────────┼──────────────────\n"
                f"Condition usage  | __________         | __________\n"
                f"Nb exécutions    | __________         | __________\n"
                f"Risque principal | __________         | __________\n"
                f"Syntaxe clé      | __________         | __________"
            ),
            'diff_body': (
                f"<strong>Objectif :</strong> Rédiger une comparaison argumentée.<br><br>"
                f"Pour la section «&nbsp;{title_sec}&nbsp;», rédigez un paragraphe qui :<br><br>"
                f"1. Présente les <strong>deux éléments</strong> comparés dans le cours.<br>"
                f"2. Explique leurs <strong>différences fondamentales</strong> avec des exemples concrets.<br>"
                f"3. Conclut sur <strong>quand utiliser l'un vs l'autre</strong>.<br><br>"
                f"<em>Conseil : appuyez-vous sur des exemples tirés directement du cours.</em>"
            ),
        },
        'erreur_piege': {
            'nom': 'Erreur / Piège',
            'facile_body': (
                f"<strong>Objectif :</strong> Identifier une erreur classique de la section «&nbsp;{title_sec}&nbsp;».<br><br>"
                f"1. Quelle est l'erreur décrite dans le cours ?<br>"
                f"2. Pourquoi cette erreur est-elle difficile à détecter ?<br>"
                f"3. Comment l'éviter systématiquement ?"
            ),
            'moyen_body': (
                f"<strong>Objectif :</strong> Trouver et corriger le bug dans ce code.<br><br>"
                f"Ce code contient une <strong>erreur classique</strong> de la section «&nbsp;{title_sec}&nbsp;».<br>"
                f"Identifiez-la, expliquez-la et écrivez la version corrigée :"
            ),
            'moyen_code': (
                "// CODE BUGUÉ — Trouver l'erreur\n"
                + ("Variable i, somme : Entier\nDébut\n   somme ← 0\n   Pour i de 1 à 10 Faire\n      i ← i + 2\n      somme ← somme + i\n   FinPour\n   Écrire(somme)\nFin"
                   if is_algo else
                   ("somme = 0\nfor i in range(1, 11):\n    i = i + 2  # erreur ici\n    somme += i\nprint(somme)"
                    if is_py else
                    "let somme = 0;\nfor (let i = 1; i <= 10; i++) {\n    i = i + 2; // erreur ici\n    somme += i;\n}\nconsole.log(somme);"
                    )
                   )
            ),
            'diff_body': (
                f"<strong>Objectif :</strong> Analyser, corriger et prévenir une erreur.<br><br>"
                f"Pour la section «&nbsp;{title_sec}&nbsp;» :<br><br>"
                f"1. Décrivez précisément l'erreur mentionnée.<br>"
                f"2. Écrivez un exemple de code <strong>incorrect</strong> illustrant cette erreur.<br>"
                f"3. Écrivez la version <strong>corrigée</strong> avec explication.<br>"
                f"4. Proposez une règle ou vérification pour <strong>ne plus commettre</strong> cette erreur.<br><br>"
                f"<em>Conseil : donnez un cas concret, pas juste une description abstraite.</em>"
            ),
        },
        'trace_execution': {
            'nom': "Trace d'Exécution",
            'facile_body': (
                f"<strong>Objectif :</strong> Comprendre le déroulement d'un algorithme de la section «&nbsp;{title_sec}&nbsp;».<br><br>"
                f"1. Combien d'itérations effectue la boucle si N = 4 ?<br>"
                f"2. Quelle est la valeur finale de la variable de résultat ?<br>"
                f"3. Que se passe-t-il si N = 0 ?"
            ),
            'moyen_body': (
                f"<strong>Objectif :</strong> Compléter le tableau de trace.<br><br>"
                f"Tracez l'exécution de l'algorithme étape par étape en remplissant les cellules vides :"
            ),
            'moyen_code': (
                "i    | condition | instruction      | somme\n"
                "─────┼───────────┼──────────────────┼──────\n"
                "init |    —      | somme ← 0        |   0\n"
                "  1  | 1 <= N ?  | somme ← 0 + 1    | ____\n"
                "  2  | 2 <= N ?  | somme ← __ + 2   | ____\n"
                "  3  | 3 <= N ?  | somme ← __ + 3   | ____\n"
                "  4  | 4 <= N ?  | somme ← __ + 4   | ____\n"
                "  5  | 5 <= N ?  | sortie boucle    | ____"
            ),
            'diff_body': (
                f"<strong>Objectif :</strong> Tracer complètement l'exécution.<br><br>"
                f"Pour l'algorithme de la section «&nbsp;{title_sec}&nbsp;», avec N = 5 :<br><br>"
                f"1. Construisez le <strong>tableau de trace complet</strong> (une ligne par itération).<br>"
                f"2. Indiquez la valeur de chaque variable après chaque étape.<br>"
                f"3. Donnez le <strong>résultat final</strong> et vérifiez-le manuellement.<br><br>"
                f"<em>Conseil : tracez chaque variable sur une colonne distincte.</em>"
            ),
        },
        'entree_sortie': {
            'nom': 'Entrées / Sorties',
            'facile_body': (
                f"<strong>Objectif :</strong> Identifier le contrat d'interface de la section «&nbsp;{title_sec}&nbsp;».<br><br>"
                f"Pour la fonction ou l'algorithme décrit :<br><br>"
                f"1. Listez toutes les <strong>données en entrée</strong> (nom, type, contrainte).<br>"
                f"2. Décrivez la <strong>valeur retournée</strong> en sortie.<br>"
                f"3. Que retourne la fonction si les données d'entrée sont invalides ?"
            ),
            'moyen_body': (
                f"<strong>Objectif :</strong> Compléter le contrat d'interface.<br><br>"
                f"Remplissez le schéma entrée/sortie de la fonction :"
            ),
            'moyen_code': (
                "FONCTION __________(________ : ________, ________ : ________) : ________\n"
                "┌─────────────────────────────────────────┐\n"
                "│  Entrées  :                              │\n"
                "│    — __________ (________) : __________  │\n"
                "│    — __________ (________) : __________  │\n"
                "│  Sortie   :                              │\n"
                "│    — __________ : __________             │\n"
                "│  Précond  : __________                   │\n"
                "└─────────────────────────────────────────┘"
            ),
            'diff_body': (
                f"<strong>Objectif :</strong> Concevoir et documenter une fonction complète.<br><br>"
                f"Pour la section «&nbsp;{title_sec}&nbsp;» :<br><br>"
                f"1. Définissez les <strong>entrées</strong> avec leur type et leurs contraintes.<br>"
                f"2. Définissez la <strong>sortie</strong> avec son type et ce qu'elle représente.<br>"
                f"3. Écrivez la <strong>signature complète</strong> de la fonction.<br>"
                f"4. Implémentez le corps de la fonction.<br><br>"
                f"<em>Conseil : commencez par le contrat avant d'écrire le code.</em>"
            ),
        },
        'preconditions': {
            'nom': 'Préconditions / Postconditions',
            'facile_body': (
                f"<strong>Objectif :</strong> Comprendre le contrat de l'algorithme «&nbsp;{title_sec}&nbsp;».<br><br>"
                f"1. Quelle est la <strong>précondition</strong> principale ? (Que doit-on garantir en entrée ?)<br>"
                f"2. Quelle est la <strong>postcondition</strong> ? (Que garantit l'algorithme en sortie ?)<br>"
                f"3. Que se passe-t-il si la précondition n'est pas respectée ?"
            ),
            'moyen_body': (
                f"<strong>Objectif :</strong> Compléter le contrat formel.<br><br>"
                f"Remplissez les blancs du contrat de l'algorithme :"
            ),
            'moyen_code': (
                "ALGORITHME : __________\n"
                "─────────────────────────────────────────\n"
                "PRÉCONDITION  : __________\n"
                "               __________\n"
                "─────────────────────────────────────────\n"
                "TRAITEMENT    : (corps de l'algorithme)\n"
                "─────────────────────────────────────────\n"
                "POSTCONDITION : __________\n"
                "               __________"
            ),
            'diff_body': (
                f"<strong>Objectif :</strong> Rédiger le contrat complet.<br><br>"
                f"Pour l'algorithme de la section «&nbsp;{title_sec}&nbsp;» :<br><br>"
                f"1. Rédigez toutes les <strong>préconditions</strong> avec justification.<br>"
                f"2. Rédigez toutes les <strong>postconditions</strong>.<br>"
                f"3. Écrivez le code qui <strong>vérifie</strong> les préconditions en début de fonction.<br>"
                f"4. Donnez un exemple d'appel <strong>valide</strong> et un appel <strong>invalide</strong>.<br><br>"
                f"<em>Conseil : pensez aux cas limites (N=0, valeur négative, tableau vide…).</em>"
            ),
        },
        'conversion_langage': {
            'nom': 'Conversion entre Langages',
            'facile_body': (
                f"<strong>Objectif :</strong> Reconnaître les équivalences de la section «&nbsp;{title_sec}&nbsp;».<br><br>"
                f"1. Identifiez la structure algorithmique principale présentée.<br>"
                f"2. Donnez sa syntaxe en <strong>algorithmique</strong>.<br>"
                f"3. Donnez son équivalent en <strong>Python</strong>.<br>"
                f"4. Donnez son équivalent en <strong>JavaScript</strong>."
            ),
            'moyen_body': (
                f"<strong>Objectif :</strong> Compléter la table de correspondance.<br><br>"
                f"Remplissez les colonnes manquantes :"
            ),
            'moyen_code': (
                "Algorithmique             | Python                | JavaScript\n"
                "──────────────────────────┼───────────────────────┼──────────────────────\n"
                "POUR i DE 1 À N FAIRE     | __________            | __________\n"
                "TANT QUE cond FAIRE       | __________            | __________\n"
                "RÉPÉTER...JUSQU'À cond    | __________            | __________\n"
                "SI cond ALORS...SINON     | __________            | __________\n"
                "FONCTION f(n:Entier):Réel | __________            | __________\n"
                "RETOURNER valeur          | __________            | __________"
            ),
            'diff_body': (
                f"<strong>Objectif :</strong> Traduire un algorithme complet.<br><br>"
                f"Pour la section «&nbsp;{title_sec}&nbsp;» :<br><br>"
                f"1. Écrivez l'algorithme complet en <strong>notation algorithmique</strong>.<br>"
                f"2. Traduisez-le intégralement en <strong>Python</strong>.<br>"
                f"3. Traduisez-le intégralement en <strong>JavaScript</strong>.<br>"
                f"4. Signalez les <strong>différences syntaxiques</strong> notables entre les trois versions.<br><br>"
                f"<em>Conseil : commencez par l'algorithmique, les autres découlent naturellement.</em>"
            ),
        },
        'complexite': {
            'nom': 'Complexité / Efficacité',
            'facile_body': (
                f"<strong>Objectif :</strong> Analyser la complexité de la section «&nbsp;{title_sec}&nbsp;».<br><br>"
                f"1. Quelle est la complexité en temps de l'algorithme ? (O(1), O(n), O(n²)…)<br>"
                f"2. Justifiez votre réponse en comptant le nombre d'opérations.<br>"
                f"3. Existe-t-il un algorithme plus efficace pour le même problème ?"
            ),
            'moyen_body': (
                f"<strong>Objectif :</strong> Comparer deux algorithmes.<br><br>"
                f"Analysez les deux algorithmes et remplissez le tableau :"
            ),
            'moyen_code': (
                "Critère               | Algo A (boucle simple) | Algo B (boucles imbriquées)\n"
                "──────────────────────┼────────────────────────┼────────────────────────────\n"
                "Nb boucles            | 1                      | 2 imbriquées\n"
                "Nb opérations (N=10)  | __________             | __________\n"
                "Nb opérations (N=100) | __________             | __________\n"
                "Complexité            | __________             | __________\n"
                "Recommandé pour       | __________             | __________"
            ),
            'diff_body': (
                f"<strong>Objectif :</strong> Analyser et optimiser un algorithme.<br><br>"
                f"Pour l'algorithme de la section «&nbsp;{title_sec}&nbsp;» :<br><br>"
                f"1. Déterminez la <strong>complexité en temps</strong> et en espace.<br>"
                f"2. Calculez le nombre d'opérations pour N=10, N=100, N=1000.<br>"
                f"3. Identifiez le <strong>goulot d'étranglement</strong> (la partie la plus coûteuse).<br>"
                f"4. Proposez une <strong>version optimisée</strong> si possible.<br><br>"
                f"<em>Conseil : comptez les boucles imbriquées pour déterminer la complexité.</em>"
            ),
        },
        'regle_absolue': {
            'nom': 'Règle Absolue',
            'facile_body': (
                f"<strong>Objectif :</strong> Retenir les règles fondamentales de la section «&nbsp;{title_sec}&nbsp;».<br><br>"
                f"1. Énoncez la règle principale décrite dans le cours.<br>"
                f"2. Donnez un exemple de code qui <strong>respecte</strong> cette règle.<br>"
                f"3. Donnez un exemple de code qui <strong>enfreint</strong> cette règle et expliquez les conséquences."
            ),
            'moyen_body': (
                f"<strong>Objectif :</strong> Compléter l'énoncé de la règle.<br><br>"
                f"Complétez chaque règle fondamentale avec le bon terme :"
            ),
            'moyen_code': (
                "Règle 1 : Il faut toujours __________ une variable avant de __________.\n"
                "Règle 2 : On ne doit jamais __________ la variable de contrôle dans une boucle __________.\n"
                "Règle 3 : Toute fonction récursive doit avoir un __________.\n"
                "Règle 4 : Un diviseur ne doit jamais valoir __________ avant une division.\n"
                "Règle 5 : Il faut toujours vérifier que l'indice est entre __ et __ pour un tableau de taille N."
            ),
            'diff_body': (
                f"<strong>Objectif :</strong> Justifier et illustrer une règle absolue.<br><br>"
                f"Pour la règle décrite dans la section «&nbsp;{title_sec}&nbsp;» :<br><br>"
                f"1. Énoncez la règle de manière précise et complète.<br>"
                f"2. Expliquez <strong>pourquoi</strong> cette règle est fondamentale.<br>"
                f"3. Donnez un exemple concret de programme qui la <strong>respecte</strong>.<br>"
                f"4. Donnez un exemple qui la <strong>viole</strong> et montrez le bug produit.<br><br>"
                f"<em>Conseil : le contre-exemple est aussi important que l'exemple positif.</em>"
            ),
        },
        'schema': {
            'nom': 'Schéma / Organigramme',
            'facile_body': (
                f"<strong>Objectif :</strong> Comprendre une représentation graphique de la section «&nbsp;{title_sec}&nbsp;».<br><br>"
                f"1. Décrivez en mots ce que représente le schéma ou l'organigramme.<br>"
                f"2. Identifiez les <strong>symboles utilisés</strong> et leur signification.<br>"
                f"3. Reliez le schéma à l'algorithme correspondant."
            ),
            'moyen_body': (
                f"<strong>Objectif :</strong> Compléter l'organigramme.<br><br>"
                f"Remplissez les éléments manquants de l'organigramme de la boucle :"
            ),
            'moyen_code': (
                "  ┌─────────────────────┐\n"
                "  │  __________         │  ← Initialisation\n"
                "  └──────────┬──────────┘\n"
                "             ↓\n"
                "   [__________?] ──Non──→  __________ (fin)\n"
                "             │ Oui\n"
                "             ↓\n"
                "   ┌─────────────────┐\n"
                "   │  __________     │  ← Corps de la boucle\n"
                "   └────────┬────────┘\n"
                "            │\n"
                "            └────────────↑  (retour condition)"
            ),
            'diff_body': (
                f"<strong>Objectif :</strong> Construire un organigramme complet.<br><br>"
                f"Pour l'algorithme de la section «&nbsp;{title_sec}&nbsp;» :<br><br>"
                f"1. Dessinez (ou décrivez précisément) l'<strong>organigramme complet</strong>.<br>"
                f"2. Utilisez les symboles standard : ovale (début/fin), rectangle (traitement), losange (décision).<br>"
                f"3. Annotez chaque bloc avec la description de l'opération.<br>"
                f"4. Indiquez les flèches et les conditions sur chaque branche.<br><br>"
                f"<em>Conseil : commencez par le début et la fin, puis remplissez le milieu.</em>"
            ),
        },
    }

    meta = META.get(pat_type)
    if not meta:
        return None

    if level == 'facile':
        return ExerciseOutput(
            level='facile',
            title=f"{meta['nom']} — {prefix}{title_sec}",
            body=meta['facile_body'],
            code=None
        )

    if level == 'moyen':
        return ExerciseOutput(
            level='moyen',
            title=f"{meta['nom']} à compléter — {prefix}{title_sec}",
            body=meta['moyen_body'],
            code=meta.get('moyen_code')
        )

    return ExerciseOutput(
        level='difficile',
        title=f"{meta['nom']} — Production — {prefix}{title_sec}",
        body=meta['diff_body'],
        code=None
    )


def _detect_best_pattern(sec) -> tuple:
    """Essaie d'abord les patterns syntaxiques (blocs de code), puis les patterns textuels.
    Retourne (type, data) ou (None, [])."""
    text = f"{sec.title}. {sec.content}"

    # ── Priorité 1 : blocs de syntaxe algorithmique ──
    for name, func in [
        ('syntaxe_pour', detect_syntaxe_pour),
        ('syntaxe_tantque', detect_syntaxe_tantque),
        ('syntaxe_repeter', detect_syntaxe_repeter),
        ('syntaxe_si', detect_syntaxe_si),
        ('syntaxe_fonction', detect_syntaxe_fonction),
        ('syntaxe_tableau', detect_syntaxe_tableau),
    ]:
        data = func(text)
        if data:
            return (name, data)

    # ── Priorité 2 : patterns analytiques (comparaison, erreur, trace…) ──
    for name, func in [
        ('comparaison',        detect_comparaison),
        ('erreur_piege',       detect_erreur_piege),
        ('trace_execution',    detect_trace_execution),
        ('entree_sortie',      detect_entree_sortie),
        ('preconditions',      detect_preconditions),
        ('conversion_langage', detect_conversion_langage),
        ('complexite',         detect_complexite),
        ('regle_absolue',      detect_regle_absolue),
        ('schema',             detect_schema),
    ]:
        data = func(text)
        if data:
            return (name, data)

    # ── Priorité 3 : patterns textuels classiques ──
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
            ex = _make_exercise(sec, d, is_pour, is_tantque, is_if, is_algo, is_py, prefix, req.appro)
            ex.section = sec
            out.append(ex)

    return out


def _make_syntaxe_exercise(sec, level, pat_type, is_algo, is_py, prefix) -> ExerciseOutput:
    """Génère un exercice de production algorithmique pour les patterns syntaxiques (26-31)."""

    SYNTAXE_META = {
        'syntaxe_pour': {
            'nom': 'Boucle POUR',
            'scenarios_algo': [
                ("Calculer la somme des entiers",
                 "Écrire un algorithme qui calcule la somme des entiers de 1 à N (N saisi par l'utilisateur).",
                 "Variable i, N, somme : Entier\nDébut\n   Écrire(\"Entrer N :\")\n   Lire(N)\n   somme ← 0\n   Pour i de 1 à N Faire\n      somme ← somme + i\n   FinPour\n   Écrire(\"Somme = \", somme)\nFin"),
                ("Saisir et afficher N notes",
                 "Écrire un algorithme qui demande N notes à l'utilisateur et les affiche une par une.",
                 "Variable i, N : Entier\nVariable note : Réel\nDébut\n   Écrire(\"Combien de notes ?\")\n   Lire(N)\n   Pour i de 1 à N Faire\n      Écrire(\"Note \", i, \" :\")\n      Lire(note)\n      Écrire(\"Note saisie : \", note)\n   FinPour\nFin"),
                ("Table de multiplication",
                 "Écrire un algorithme qui affiche la table de multiplication d'un entier saisi.",
                 "Variable n, i : Entier\nDébut\n   Écrire(\"Entrer un entier :\")\n   Lire(n)\n   Pour i de 1 à 10 Faire\n      Écrire(n, \" × \", i, \" = \", n*i)\n   FinPour\nFin"),
            ],
            'scenarios_py': [
                ("Calculer la somme des entiers",
                 "Écrire une fonction Python qui calcule la somme des entiers de 1 à N.",
                 "def somme_entiers(N):\n    total = 0\n    for i in range(1, N + 1):\n        total += i\n    return total\n\nN = int(input(\"Entrer N : \"))\nprint(\"Somme =\", somme_entiers(N))"),
                ("Saisir et afficher N notes",
                 "Écrire un programme Python qui saisit N notes et calcule la moyenne.",
                 "N = int(input(\"Nombre de notes : \"))\nnotes = []\nfor i in range(N):\n    note = float(input(f\"Note {i+1} : \"))\n    notes.append(note)\nprint(\"Moyenne :\", sum(notes) / N)"),
            ],
            'scenarios_js': [
                ("Table de multiplication",
                 "Écrire une fonction JavaScript qui affiche la table de multiplication.",
                 "function tableMultiplication(n) {\n  for (let i = 1; i <= 10; i++) {\n    console.log(`${n} × ${i} = ${n * i}`);\n  }\n}\ntableMultiplication(parseInt(prompt('Entier :')));"),
            ],
            'trous_algo': "Variable i, N, somme : Entier\nDébut\n   Lire(N)\n   somme ← __\n   Pour i de __ à N Faire\n      somme ← somme + __\n   FinPour\n   Écrire(somme)\nFin",
            'trous_py':   "N = int(input())\ntotal = __\nfor i in range(__, __ + 1):\n    total += __\nprint(total)",
            'trous_js':   "let total = __;\nfor (let i = __; i <= N; i++) {\n    total += __;\n}\nconsole.log(total);",
        },
        'syntaxe_tantque': {
            'nom': 'Boucle TANT QUE',
            'scenarios_algo': [
                ("Lire jusqu'à 0",
                 "Écrire un algorithme qui lit des entiers positifs et s'arrête quand l'utilisateur saisit 0. Il affiche la somme.",
                 "Variable n, somme : Entier\nDébut\n   somme ← 0\n   Lire(n)\n   Tant que n != 0 Faire\n      somme ← somme + n\n      Lire(n)\n   FinTantQue\n   Écrire(\"Somme = \", somme)\nFin"),
                ("Compte à rebours",
                 "Écrire un algorithme qui affiche un compte à rebours de N jusqu'à 0.",
                 "Variable N : Entier\nDébut\n   Écrire(\"Entrer N :\")\n   Lire(N)\n   Tant que N >= 0 Faire\n      Écrire(N)\n      N ← N - 1\n   FinTantQue\nFin"),
            ],
            'scenarios_py': [
                ("Lire jusqu'à 0",
                 "Écrire un programme Python qui lit des entiers jusqu'à la saisie de 0 et affiche leur somme.",
                 "somme = 0\nn = int(input(\"Entier (0 pour arrêter) : \"))\nwhile n != 0:\n    somme += n\n    n = int(input(\"Entier : \"))\nprint(\"Somme =\", somme)"),
            ],
            'scenarios_js': [
                ("Deviner un nombre",
                 "Écrire un programme JavaScript où l'utilisateur devine un nombre secret avec while.",
                 "const secret = 42;\nlet essai;\nwhile (essai !== secret) {\n  essai = parseInt(prompt('Devinez le nombre :'));\n  if (essai < secret) console.log('Trop petit !');\n  else if (essai > secret) console.log('Trop grand !');\n}\nconsole.log('Bravo !');"),
            ],
            'trous_algo': "Variable n, somme : Entier\nDébut\n   somme ← 0\n   Lire(n)\n   Tant que __ Faire\n      somme ← somme + n\n      __\n   FinTantQue\n   Écrire(somme)\nFin",
            'trous_py':   "somme = 0\nn = int(input())\nwhile __:\n    somme += n\n    n = int(input())\nprint(somme)",
            'trous_js':   "let somme = 0, n;\nn = parseInt(prompt());\nwhile (__) {\n    somme += n;\n    n = parseInt(__);\n}\nconsole.log(somme);",
        },
        'syntaxe_repeter': {
            'nom': "Boucle RÉPÉTER JUSQU'À",
            'scenarios_algo': [
                ("Validation de saisie",
                 "Écrire un algorithme qui force l'utilisateur à saisir un entier strictement positif (refus tant que la valeur est ≤ 0).",
                 "Variable n : Entier\nDébut\n   Répéter\n      Écrire(\"Saisir un entier positif :\")\n      Lire(n)\n      Si n <= 0 Alors\n         Écrire(\"Valeur invalide !\")\n      FinSi\n   Jusqu'à (n > 0)\n   Écrire(\"Valeur acceptée : \", n)\nFin"),
                ("Menu interactif",
                 "Écrire un algorithme qui affiche un menu (1-Ajouter, 2-Supprimer, 0-Quitter) et répète jusqu'au choix 0.",
                 "Variable choix : Entier\nDébut\n   Répéter\n      Écrire(\"1-Ajouter  2-Supprimer  0-Quitter\")\n      Lire(choix)\n      Si choix = 1 Alors Écrire(\"Ajout...\")\n      Sinon Si choix = 2 Alors Écrire(\"Suppression...\")\n      FinSi\n   Jusqu'à (choix = 0)\n   Écrire(\"Au revoir !\")\nFin"),
            ],
            'scenarios_py': [
                ("Validation de saisie",
                 "Python n'a pas de do-while natif. Écrire l'équivalent avec while True et break.",
                 "while True:\n    n = int(input(\"Saisir un entier positif : \"))\n    if n > 0:\n        break\n    print(\"Valeur invalide !\")\nprint(\"Valeur acceptée :\", n)"),
            ],
            'scenarios_js': [
                ("Menu interactif",
                 "Écrire un menu interactif en JavaScript avec do...while.",
                 "let choix;\ndo {\n  choix = parseInt(prompt('1-Ajouter  2-Supprimer  0-Quitter'));\n  if (choix === 1) console.log('Ajout...');\n  else if (choix === 2) console.log('Suppression...');\n} while (choix !== 0);\nconsole.log('Au revoir !');"),
            ],
            'trous_algo': "Variable n : Entier\nDébut\n   __\n      Écrire(\"Saisir un positif :\")\n      Lire(n)\n   __ (n > 0)\n   Écrire(n)\nFin",
            'trous_py':   "while __:\n    n = int(input(\"Saisir un positif : \"))\n    if n > 0:\n        __\n    print(\"Invalide\")\nprint(n)",
            'trous_js':   "let n;\ndo {\n  n = parseInt(prompt('Saisir un positif :'));\n} while (__);\nconsole.log(n);",
        },
        'syntaxe_si': {
            'nom': 'Structure SI / SINON',
            'scenarios_algo': [
                ("Classifier une note",
                 "Écrire un algorithme qui lit une note et affiche : 'Très bien' (≥16), 'Bien' (≥13), 'Passable' (≥10), 'Insuffisant' (<10).",
                 "Variable note : Réel\nDébut\n   Écrire(\"Entrer la note :\")\n   Lire(note)\n   Si note >= 16 Alors\n      Écrire(\"Très bien\")\n   Sinon Si note >= 13 Alors\n      Écrire(\"Bien\")\n   Sinon Si note >= 10 Alors\n      Écrire(\"Passable\")\n   Sinon\n      Écrire(\"Insuffisant\")\n   FinSi\nFin"),
                ("Pair ou impair",
                 "Écrire un algorithme qui détermine si un entier saisi est pair ou impair.",
                 "Variable n : Entier\nDébut\n   Lire(n)\n   Si (n MOD 2 = 0) Alors\n      Écrire(n, \" est pair\")\n   Sinon\n      Écrire(n, \" est impair\")\n   FinSi\nFin"),
            ],
            'scenarios_py': [
                ("Classifier une note",
                 "Écrire une fonction Python qui classe une note sur 20.",
                 "def classifier_note(note):\n    if note >= 16:\n        return 'Très bien'\n    elif note >= 13:\n        return 'Bien'\n    elif note >= 10:\n        return 'Passable'\n    else:\n        return 'Insuffisant'\n\nnote = float(input('Note : '))\nprint(classifier_note(note))"),
            ],
            'scenarios_js': [
                ("Calculatrice simple",
                 "Écrire une fonction JavaScript qui effectue +, -, ×, ÷ selon le signe saisi.",
                 "function calculer(a, op, b) {\n  if (op === '+') return a + b;\n  else if (op === '-') return a - b;\n  else if (op === '*') return a * b;\n  else if (op === '/') return b !== 0 ? a / b : 'Division par zéro';\n  else return 'Opérateur inconnu';\n}"),
            ],
            'trous_algo': "Variable note : Réel\nDébut\n   Lire(note)\n   __ note >= 10 __ \n      Écrire(\"Admis\")\n   __\n      Écrire(\"Échec\")\n   FinSi\nFin",
            'trous_py':   "note = float(input())\n__ note >= 10:\n    print('Admis')\n__:\n    print('Échec')",
            'trous_js':   "let note = parseFloat(prompt());\nif (__) {\n    console.log('Admis');\n} __ {\n    console.log('Échec');\n}",
        },
        'syntaxe_fonction': {
            'nom': 'Fonctions et Procédures',
            'scenarios_algo': [
                ("Fonction carré",
                 "Écrire une fonction Carré(n) qui retourne le carré d'un entier, puis un programme principal qui l'appelle pour 5 valeurs.",
                 "Fonction Carré(n : Entier) : Entier\nDébut\n   Retourner n * n\nFin\n\n// Programme principal\nVariable i, res : Entier\nDébut\n   Pour i de 1 à 5 Faire\n      res ← Carré(i)\n      Écrire(i, \"² = \", res)\n   FinPour\nFin"),
                ("Procédure afficher étoiles",
                 "Écrire une procédure AfficherLigne(n) qui affiche n étoiles, puis l'appeler 3 fois.",
                 "Procédure AfficherLigne(n : Entier)\nVariable i : Entier\nDébut\n   Pour i de 1 à n Faire\n      Écrire(\"*\")\n   FinPour\n   Écrire(\"\\n\")\nFin\n\n// Programme principal\nDébut\n   AfficherLigne(3)\n   AfficherLigne(5)\n   AfficherLigne(7)\nFin"),
            ],
            'scenarios_py': [
                ("Fonction factorielle",
                 "Écrire une fonction Python factorielle(n) qui calcule n! et la tester.",
                 "def factorielle(n):\n    if n <= 1:\n        return 1\n    return n * factorielle(n - 1)\n\nfor i in range(1, 8):\n    print(f\"{i}! = {factorielle(i)}\")"),
            ],
            'scenarios_js': [
                ("Fonction maximum",
                 "Écrire une fonction JavaScript qui retourne le maximum de deux nombres.",
                 "function maximum(a, b) {\n  return a >= b ? a : b;\n}\n\nconsole.log(maximum(12, 7));   // 12\nconsole.log(maximum(3, 15));   // 15"),
            ],
            'trous_algo': "Fonction Carre(n : __) : Entier\nDébut\n   Retourner __ * __\nFin\n\n// Appel\nVariable res : Entier\nDébut\n   res ← __(5)\n   Écrire(res)\nFin",
            'trous_py':   "def carre(n):\n    return __ * __\n\nfor i in range(1, 6):\n    print(i, '² =', __(i))",
            'trous_js':   "function carre(n) {\n    return __ * __;\n}\nconsole.log(__(5));",
        },
        'syntaxe_tableau': {
            'nom': 'Tableaux et Listes',
            'scenarios_algo': [
                ("Saisie et maximum",
                 "Écrire un algorithme qui saisit 10 entiers dans un tableau et affiche le plus grand.",
                 "Variable T : Tableau[0..9] de Entier\nVariable i, max : Entier\nDébut\n   Pour i de 0 à 9 Faire\n      Écrire(\"T[\", i, \"] = \")\n      Lire(T[i])\n   FinPour\n   max ← T[0]\n   Pour i de 1 à 9 Faire\n      Si T[i] > max Alors\n         max ← T[i]\n      FinSi\n   FinPour\n   Écrire(\"Maximum = \", max)\nFin"),
                ("Somme et moyenne",
                 "Écrire un algorithme qui remplit un tableau de N notes et calcule leur moyenne.",
                 "Variable notes : Tableau[0..N-1] de Réel\nVariable i, N : Entier\nVariable somme, moyenne : Réel\nDébut\n   Lire(N)\n   somme ← 0\n   Pour i de 0 à N-1 Faire\n      Lire(notes[i])\n      somme ← somme + notes[i]\n   FinPour\n   moyenne ← somme / N\n   Écrire(\"Moyenne = \", moyenne)\nFin"),
            ],
            'scenarios_py': [
                ("Saisie et maximum",
                 "Écrire un programme Python qui saisit N valeurs dans une liste et affiche le maximum.",
                 "N = int(input('Taille : '))\nvaleurs = []\nfor i in range(N):\n    valeurs.append(float(input(f'valeurs[{i}] = ')))\nprint('Maximum :', max(valeurs))"),
            ],
            'scenarios_js': [
                ("Moyenne d'un tableau",
                 "Écrire une fonction JavaScript qui calcule la moyenne d'un tableau de nombres.",
                 "function moyenne(tab) {\n  const somme = tab.reduce((acc, v) => acc + v, 0);\n  return somme / tab.length;\n}\n\nconst notes = [12, 15, 9, 17, 11];\nconsole.log('Moyenne :', moyenne(notes));"),
            ],
            'trous_algo': "Variable T : Tableau[0..__] de Entier\nVariable i, max : Entier\nDébut\n   Pour i de __ à 9 Faire\n      Lire(T[__])\n   FinPour\n   max ← T[0]\n   Pour i de 1 à 9 Faire\n      Si T[i] > __ Alors\n         max ← __\n      FinSi\n   FinPour\nFin",
            'trous_py':   "valeurs = []\nfor i in range(N):\n    valeurs.__(float(input()))\nmaxi = valeurs[__]\nfor v in valeurs:\n    if v > maxi:\n        maxi = __\nprint(maxi)",
            'trous_js':   "let tab = [];\nfor (let i = 0; i < N; i++) {\n    tab.__(parseFloat(prompt()));\n}\nlet max = tab[__];\nfor (let v of tab) {\n    if (v > max) max = __;\n}\nconsole.log(max);",
        },
    }

    meta = SYNTAXE_META.get(pat_type)
    if not meta:
        return None

    scenarios = meta['scenarios_algo'] if is_algo else (meta['scenarios_py'] if is_py else meta['scenarios_js'])
    if not scenarios:
        scenarios = meta['scenarios_algo']

    import random
    scenario = random.choice(scenarios)
    titre_scenario, enonce, code_exemple = scenario

    if level == 'facile':
        return ExerciseOutput(
            level='facile',
            title=f"Syntaxe — {meta['nom']} : {titre_scenario}",
            body=(
                f"<strong>Objectif :</strong> Comprendre et utiliser la {meta['nom']}.<br><br>"
                f"<strong>Énoncé :</strong> {enonce}<br><br>"
                f"<em>Conseil : identifiez d'abord la structure à utiliser, "
                f"puis déclarez vos variables avant d'écrire le corps.</em>"
            ),
            code=None
        )

    if level == 'moyen':
        trou = meta['trous_algo'] if is_algo else (meta['trous_py'] if is_py else meta['trous_js'])
        return ExerciseOutput(
            level='moyen',
            title=f"Compléter la syntaxe — {meta['nom']}",
            body=(
                f"<strong>Objectif :</strong> Compléter le code manquant pour faire fonctionner l'algorithme.<br><br>"
                f"Remplacez chaque <code>__</code> par le bon mot-clé ou la bonne valeur :"
            ),
            code=trou
        )

    # Niveau difficile
    return ExerciseOutput(
        level='difficile',
        title=f"Production — {meta['nom']} : {titre_scenario}",
        body=(
            f"<strong>Objectif :</strong> Écrire un programme complet de zéro.<br><br>"
            f"<strong>Énoncé :</strong> {enonce}<br><br>"
            f"<em>Conseil : testez votre algorithme avec des valeurs connues avant de rendre.</em>"
        ),
        code=code_exemple
    )


def _make_exercise(sec, level, is_pour, is_tantque, is_if, is_algo, is_py, prefix, appro) -> ExerciseOutput:
    """Fabrique un exercice selon le pattern détecté et le niveau."""

    # ── Détection unique du meilleur pattern ──
    pat_type, pat_data = _detect_best_pattern(sec)

    # ── Si pattern syntaxique détecté → exercice de production dédié ──
    if pat_type and pat_type.startswith('syntaxe_'):
        ex = _make_syntaxe_exercise(sec, level, pat_type, is_algo, is_py, prefix)
        if ex:
            return ex

    # ── Si pattern analytique détecté → exercice d'analyse dédié ──
    _ANALYSE_PATTERNS = {
        'comparaison', 'erreur_piege', 'trace_execution', 'entree_sortie',
        'preconditions', 'conversion_langage', 'complexite', 'regle_absolue', 'schema'
    }
    if pat_type and pat_type in _ANALYSE_PATTERNS:
        ex = _make_analyse_exercise(sec, level, pat_type, is_algo, is_py, prefix)
        if ex:
            return ex

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

        # ★ FALLBACK : Questions génériques basées sur le titre de la section
        sec_kw = sec.title.strip()
        items = [
            f"Expliquez en vos propres mots : {sec_kw}.",
            f"Donnez un exemple concret illustrant {sec_kw}.",
            f"Quelle est l'utilité principale de {sec_kw} ?",
        ]
        items_html = '<br>'.join([f"{i+1}. {it}" for i, it in enumerate(items)])
        return ExerciseOutput(
            level='facile',
            title=f"Questions de cours — {prefix}{sec.title}",
            body=f"<strong>Objectif :</strong> Vérifier la compréhension de ce chapitre.<br><br>"
                 f"Répondez aux questions suivantes :<br><br>"
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

    # Si la section d'origine est fournie, générer un exercice difficile basé sur son contenu réel
    if req.section:
        sec = req.section
        key = f"{sec.title} {sec.content}".lower()
        is_pour    = bool(re.search(r'\bpour\b|boucle pour|\bfor\b|nb fois|nombre de fois', key))
        is_tantque = bool(re.search(r'tant que|tantque|while|répéter|jusqu\'à', key))
        is_if      = bool(re.search(r'\bsi\b|sinon|alternative|condition|\bif\b|\belse\b', key))
        prefix = f"{sec.num} — " if sec.num else ""

        ex = _make_exercise(sec, 'difficile', is_pour, is_tantque, is_if, is_algo, is_py, prefix, appro=True)
        return ExerciseOutput(
            level='difficile',
            title=f"▲ Version Approfondie — {ex.title}",
            body=ex.body,
            code=ex.code
        )

    # Fallback générique si aucune section fournie
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
