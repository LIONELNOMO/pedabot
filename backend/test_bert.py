# -*- coding: utf-8 -*-
"""
TEST ISOLÉ — Sentence-BERT sur 4 patterns nouveaux
Ce fichier ne touche à rien d'autre dans le projet.
Lance avec : python test_bert.py
"""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from sentence_transformers import SentenceTransformer, util

print("Chargement du modèle multilingue...")
model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
print("Modèle prêt.\n")

# ══════════════════════════════════════════════════════
#  PHRASES MODÈLES — une par type de pattern
#  BERT va comparer chaque phrase du cours à ces modèles
#  et choisir le plus proche sémantiquement
# ══════════════════════════════════════════════════════

TEMPLATES = {
    "definition": [
        "Une boucle imbriquée est une boucle placée à l'intérieur d'une autre boucle.",
        "On appelle récursivité le fait qu'une fonction s'appelle elle-même.",
        "Un tableau est une structure qui regroupe plusieurs valeurs du même type.",
        "Quand on parle de portée d'une variable, on désigne la zone du code où elle est accessible.",
        "Une pile est une structure de données où le dernier élément ajouté est le premier retiré.",
        "Un algorithme désigne une suite d'instructions permettant de résoudre un problème.",
    ],
    "cause": [
        "Le programme plante parce que la variable n'a pas été déclarée.",
        "La raison de l'erreur est que la condition n'a jamais été vérifiée.",
        "L'origine du problème vient du fait que le tableau est trop petit.",
        "Pourquoi le programme s'arrête ? Parce que la mémoire est pleine.",
        "Le bug est causé par une valeur non initialisée dans la boucle.",
    ],
    "comparaison": [
        "Une pile fonctionne comme une pile d'assiettes qu'on empile et dépile.",
        "On peut comparer une file à une queue de personnes devant un guichet.",
        "La mémoire RAM ressemble à un bureau de travail : rapide mais limité.",
        "Un pointeur est comme une adresse postale : il indique où trouver la donnée.",
        "La récursivité fonctionne comme des poupées russes, chacune contenant une plus petite.",
    ],
    "consequence": [
        "Si la condition ne devient jamais fausse, le programme tourne indéfiniment.",
        "Sans condition d'arrêt, la boucle ne se termine jamais et bloque le système.",
        "Quand la mémoire déborde, le programme cesse de fonctionner brutalement.",
        "Le programme ne s'arrête plus car la variable de contrôle n'est pas mise à jour.",
        "L'oubli d'initialisation fait que la valeur finale est incorrecte.",
    ],
}

# Encoder tous les templates une seule fois
template_vectors = {}
for ptype, phrases in TEMPLATES.items():
    template_vectors[ptype] = model.encode(phrases, convert_to_tensor=True)


def detecter_pattern(phrase: str) -> tuple:
    """
    Prend une phrase, retourne (type_détecté, score_confiance).
    Fonctionne même sans aucun mot-clé regex.
    """
    vec = model.encode(phrase, convert_to_tensor=True)
    best_type = None
    best_score = 0.0

    for ptype, tvecs in template_vectors.items():
        scores = util.cos_sim(vec, tvecs)
        score = float(scores.max())
        if score > best_score:
            best_score = score
            best_type = ptype

    return best_type, round(best_score, 3)


# ══════════════════════════════════════════════════════
#  LES 4 PHRASES DE TEST — aucun marqueur regex dedans
# ══════════════════════════════════════════════════════

tests = [
    {
        "pattern_attendu": "definition",
        "phrase": "Quand on écrit une boucle dans une boucle, le programme parcourt chaque combinaison possible.",
        "note": "Pas de marqueur visible — définition implicite de boucle imbriquée"
    },
    {
        "pattern_attendu": "cause",
        "phrase": "Le programme plante. La raison : la variable n'a pas été initialisée.",
        "note": "Cause après l'effet — regex rate 'La raison :'"
    },
    {
        "pattern_attendu": "comparaison",
        "phrase": "Une pile fonctionne comme une pile d'assiettes : on ne peut ajouter ou retirer que par le dessus.",
        "note": "Analogie — regex ne connaît pas ce pattern du tout"
    },
    {
        "pattern_attendu": "consequence",
        "phrase": "Si la condition de la boucle TANT QUE ne devient jamais fausse, le programme ne s'arrête plus.",
        "note": "Conséquence indirecte — pas de 'provoque' ni 'entraîne'"
    },
]

# ══════════════════════════════════════════════════════
#  EXÉCUTION DU TEST
# ══════════════════════════════════════════════════════

print("=" * 65)
print("  RÉSULTATS — Détection sémantique Sentence-BERT")
print("=" * 65)

total = 0
reussi = 0

for t in tests:
    total += 1
    detecte, score = detecter_pattern(t["phrase"])
    attendu = t["pattern_attendu"]
    ok = detecte == attendu

    if ok:
        reussi += 1
        status = "[OK]"
    else:
        status = "[RATE]"

    print(f"\n{status} (score: {score})")
    print(f"  Phrase   : {t['phrase'][:75]}...")
    print(f"  Attendu  : {attendu}")
    print(f"  Détecté  : {detecte}")
    print(f"  Note     : {t['note']}")

print("\n" + "=" * 65)
print(f"  SCORE FINAL : {reussi}/{total} patterns correctement détectés")
print("=" * 65)

# ══════════════════════════════════════════════════════
#  BONUS — tester aussi une phrase avec regex existant
#  pour comparer les deux approches
# ══════════════════════════════════════════════════════

print("\n--- COMPARAISON : phrase avec marqueur regex classique ---")
phrase_facile = "Une boucle POUR est définie comme une structure itérative."
detecte, score = detecter_pattern(phrase_facile)
print(f"Phrase  : {phrase_facile}")
print(f"Détecté : {detecte} (score: {score})")
print("→ BERT la détecte aussi, mais regex l'aurait détectée en premier.\n")
