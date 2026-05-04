# PédaBot — Analyse Architecturale Complète

> Assistant intelligent de consolidation pédagogique  
> Système éducatif francophone — Afrique Centrale

---

## 1. Vue Globale du Projet

PédaBot est une **application web full-stack** permettant à un enseignant de coller un cours (algorithmique, Python ou JavaScript), puis d'obtenir automatiquement des exercices pédagogiques structurés en 3 niveaux de difficulté.

Le flux est entièrement guidé par un **wizard conversationnel** : l'interface imite un chatbot qui pose des questions étape par étape, et chaque réponse de l'utilisateur fait avancer la machine d'état.

**Contexte de déploiement :**
- Frontend : React/Vite (local ou hébergé)
- Backend : FastAPI sur Render → `https://pedabot6backend.onrender.com`
- Pas de base de données. Pas de LLM externe. Tout le moteur est **purement algorithmique** (regex + pattern matching).

---

## 2. Architecture

```
prototype laure/
├── backend/
│   ├── main.py          → API FastAPI (3 routes POST)
│   ├── models.py        → Contrats de données Pydantic
│   ├── engine.py        → Cerveau du système (1800+ lignes, 25 patterns)
│   └── requirements.txt → fastapi, uvicorn, pydantic
│
├── pedabot-react/
│   └── src/
│       ├── main.jsx              → Point d'entrée React
│       ├── App.jsx               → Routeur Login ↔ Dashboard
│       ├── context/
│       │   └── AppContext.jsx    → État global (wizard, messages, thème)
│       └── components/
│           ├── Login.jsx         → Écran d'accueil / identification
│           ├── Dashboard.jsx     → Shell 3 colonnes (Sidebar + Chat + RightPanel)
│           ├── Navbar.jsx        → Barre du haut + stepper 4 étapes
│           ├── Sidebar.jsx       → Zone cours + bouton Analyser → appel /api/analyze
│           ├── ChatArea.jsx      → Moteur du wizard (machine à états + input)
│           ├── MessageItem.jsx   → Dispatcher de composants par type de message
│           └── RightPanel.jsx    → Stats + progression + export PDF
│
├── pedabot.html         → Version HTML monolithique (prototype d'origine)
└── start_pedabot.bat    → Lanceur Windows (démarre backend + ouvre navigateur)
```

### Couches du système

```
[ Utilisateur ]
      │
      ▼
[ React SPA ]  ←── AppContext (état global)
      │
      ├── Sidebar → POST /api/analyze  ──►  [ FastAPI ]
      ├── ChatArea / RecapMessage → POST /api/generate  ──►  [ FastAPI ]
      └── ExerciseMessage → POST /api/deepen  ──►  [ FastAPI ]
                                                         │
                                                    engine.py
                                                    (25 patterns regex)
```

---

## 3. Mécanismes de Fonctionnement

### 3.1 Backend — Les 4 Moteurs de `engine.py`

Le backend ne fait **aucun appel à un LLM**. Tout repose sur de l'analyse de texte par regex.

#### Moteur 1 — Détection des sections
Analyse le texte ligne par ligne avec 5 familles de patterns :
- Chiffres romains : `I. II. III.`
- Chiffres arabes : `1. 2. 3.`
- Lettres : `A. B. C.`
- Mots-clés : `Chapitre / Partie / Section`
- Markdown : `## ###`

Retourne jusqu'à **7 sections** avec `{num, title, content}`.

#### Moteur 2 — Détection de syntaxe
Compte la fréquence de mots-clés dans le texte :
- Algorithmique → `tant que`, `pour ... faire`, `début`, `fin`, `écrire`, `lire`
- Python → `def`, `print(`, `import`, `range(`
- JavaScript → `function`, `const`, `let`, `=>`

Le langage avec le plus de hits gagne.

#### Moteur 3 — Générateur d'exercices (`generate_exercises`)
Pour chaque section × difficulté :
1. Appelle `_detect_best_pattern(sec)` → essaie les 25 patterns dans l'ordre
2. Fabrique un exercice avec `_make_exercise()`

**Niveau Facile** → Questions de rappel (Q/A directes issues des patterns détectés)  
**Niveau Moyen** → Texte à trous (mots-clés remplacés par `__________`)  
**Niveau Difficile** → Production libre (rédiger, coder, analyser)

Si aucun pattern ne correspond → fallback sur des exercices génériques de programmation (boucles, conditions).

#### Moteur 4 — Approfondissement (`deepen_exercise`)
Prend le titre et le langage d'un exercice existant et génère une version plus complexe avec cas limites et défis bonus.

### 3.2 Les 25 Patterns de Reconnaissance

L'engine reconnaît 25 structures sémantiques dans un texte :

| # | Pattern | Question générée |
|---|---------|-----------------|
| 1 | Définitions | Qu'est-ce qu'un X ? |
| 2 | Causes/Origines | Quelles sont les causes de X ? |
| 3 | Conséquences/Effets | Quelles sont les conséquences de X ? |
| 4 | Étapes/Processus | Quelles sont les étapes de X ? |
| 5 | Caractéristiques | Quelles sont les caractéristiques de X ? |
| 6 | Fonctions/Rôles | À quoi sert X ? |
| 7 | Exemples | Citez des exemples de X. |
| 8 | Dates/Événements | En quelle année X a-t-il eu lieu ? |
| 9 | Avantages/Inconvénients | Citez un avantage et un inconvénient de X. |
| 10 | Classifications | Quels sont les différents types de X ? |
| 11 | Conditions/Critères | Quelles sont les conditions pour X ? |
| 12 | Acteurs/Auteurs | Qui a découvert / proposé X ? |
| 13 | Formules/Théorèmes | Quelle est la formule de X ? |
| 14 | Chiffres/Statistiques | Quel chiffre correspond à X ? |
| 15 | Localisation | Où se situe X ? |
| 16 | Composition/Structure | De quoi est composé X ? |
| 17 | Synonymes | Quels sont les synonymes de X ? |
| 18 | Exceptions | Quelle est l'exception concernant X ? |
| 19 | Abréviations | Que signifie l'acronyme X ? |
| 20 | Formats/Tableaux C | Quel format utilise-t-on pour X ? |
| 21 | Notes/Remarques (NB) | Quelle information importante concerne X ? |
| 22 | Traductions Algo↔Code | Comment traduit-on X en langage code ? |
| 23 | Objectifs/Finalités | Quel est l'objectif de X ? |
| 24 | Structure/Syntaxe | Quelle est la structure de la syntaxe de X ? |
| 25 | (fallback programmation) | Exercices génériques boucles/conditions |

### 3.3 Frontend — Machine à États du Wizard

L'état central est `step` dans `AppContext`. Il pilote tout le comportement conversationnel.

```
IDLE
  │  (utilisateur colle son cours → clic "Analyser")
  │  → appel /api/analyze
  ▼
WAIT_NAME
  │  (bot demande le nom de la série)
  │  → saisie utilisateur
  ▼
WAIT_SECTIONS
  │  (bot affiche checkboxes des sections détectées)
  │  → sélection + confirmation
  ▼
WAIT_DIFF
  │  (bot affiche 4 boutons de difficulté)
  │  → clic utilisateur
  ▼
WAIT_CONFIRM
  │  (bot affiche récapitulatif : nom / sections / difficulté / syntaxe)
  │  → "Générer" → appel /api/generate
  ▼
DONE
  │  (bot affiche les exercices sous forme de cartes)
  │  → bouton "Approfondir" sur chaque carte → appel /api/deepen
  │  → bouton "Exporter en PDF" dans RightPanel
```

---

## 4. Flux Principaux

### Flux 1 — Analyse du cours

```
[Sidebar] utilisateur colle texte → clic "Analyser le cours"
    │
    └── POST /api/analyze { courseText }
            │
            ▼
        engine.analyze_course()
            ├── detect_lang()   → algo | python | javascript
            └── detect_sections() → [{num, title, content}]
            │
            ▼
        { lang, langLabel, sections }
    │
    └── AppContext: step → WAIT_NAME, wizardDraft.sections = [...], wizardDraft.lang = "algo"
    └── Chat: message bot avec syntaxe détectée + nb de sections + prompt "Quel nom ?"
```

### Flux 2 — Génération des exercices

```
[RecapMessage] clic "Générer les exercices"
    │
    └── POST /api/generate {
            exName, difficulty, lang, appro,
            sections: [selSections]
        }
            │
            ▼
        engine.generate_exercises()
            ├── Pour chaque section :
            │     ├── _detect_best_pattern() → essaie les 25 patterns
            │     └── _make_exercise(level) → ExerciseOutput
            └── Si difficulty == "progressif" → 3 exercices par section (facile/moyen/difficile)
            │
            ▼
        { exercises: [{ level, title, body, code }] }
    │
    └── Chat: une ExerciseCard par exercice
    └── AppContext: step → DONE, stats mises à jour
```

### Flux 3 — Approfondissement

```
[ExerciseMessage] clic "+ Approfondir cet exercice"
    │
    └── POST /api/deepen { exerciseTitle, lang }
            │
            ▼
        engine.deepen_exercise()
            → génère version complexe avec cas limites
            │
            ▼
        { exercise: { level, title, body, code } }
    │
    └── Chat: nouvelle ExerciseCard ajoutée sous l'originale
```

### Flux 4 — Export PDF

```
[RightPanel] clic "Exporter en PDF" (visible uniquement si step === 'DONE')
    │
    └── Collecte tous les messages de type 'exercise' dans l'historique
    └── Génère un document HTML complet (styles inline, cartes par niveau)
    └── Ouvre une nouvelle fenêtre navigateur → window.print()
    (Pas d'appel serveur — génération 100% côté client)
```

---

## 5. Gestion des États — AppContext

| State | Type | Rôle |
|-------|------|------|
| `user` | string | Nom saisi à la connexion. Si vide → affiche Login |
| `theme` | 'light' \| 'dark' | Persiste dans localStorage |
| `step` | enum | Pilote la machine à états du wizard |
| `wizardDraft` | object | Accumule les choix de l'utilisateur au fil des étapes |
| `messages` | array | Historique conversationnel (source de vérité de tout le chat) |

**wizardDraft** évolue ainsi :

```
{ exName: '', sections: [], selSections: [], difficulty: '', lang: 'algo', appro: false }
    ↓ après /api/analyze
{ ..., lang: 'python', sections: [{num, title, content}, ...], courseText: '...' }
    ↓ après WAIT_NAME
{ ..., exName: 'TP Boucles — Seconde A' }
    ↓ après WAIT_SECTIONS
{ ..., selSections: [{...}, {...}] }
    ↓ après WAIT_DIFF
{ ..., difficulty: 'progressif' }
    ↓ après génération
{ ..., exCount: 6, secCount: 2 }
```

---

## 6. Composants et Responsabilités

| Composant | Responsabilité unique |
|-----------|----------------------|
| `Login` | Capture du nom → passe `user` dans le context → déclenche affichage Dashboard |
| `Dashboard` | Shell pur, aucune logique. Assemble les 4 blocs visuels |
| `Navbar` | Affiche le stepper 1→4 en lisant `step`, toggle dark mode |
| `Sidebar` | Seul composant qui appelle `/api/analyze`. Gère textarea + import fichier |
| `ChatArea` | Orchestre la saisie libre (réponse au WAIT_NAME). Gère l'auto-scroll |
| `MessageItem` | Dispatcher : switch sur `msg.type` → rend le bon sous-composant |
| `SectionsMessage` | Checkboxes interactives, confirme les sections → step WAIT_DIFF |
| `DifficultyMessage` | 4 boutons (facile/moyen/difficile/progressif) → step WAIT_CONFIRM |
| `RecapMessage` | Résumé + appelle `/api/generate` |
| `ExerciseMessage` | Affiche une carte exercice + bouton "Approfondir" → appelle `/api/deepen` |
| `RightPanel` | Stats réactives, barre de progression, conseils contextuels, export PDF |

---

## 7. Points Clés et Décisions Architecturales

### Zero LLM
Tout le moteur d'analyse est du **regex pur**. Avantage : pas de latence réseau vers un LLM, pas de coût API, fonctionne offline. Limite : la qualité des exercices dépend entièrement de la richesse du lexique regex.

### Messages comme source de vérité
L'historique `messages[]` est la seule source de vérité pour les exercices. Le RightPanel collecte `messages.filter(m => m.type === 'exercise')` pour l'export PDF. Pas de store séparé pour les exercices générés.

### Wizard in-chat vs formulaire
Choix délibéré d'un pattern conversationnel : chaque étape du wizard est un **message dans le chat** avec des composants interactifs (checkboxes, boutons). Cela crée une expérience plus naturelle qu'un formulaire multi-pages.

### Composants auto-contenus
Chaque sous-composant de `MessageItem` (SectionsMessage, DifficultyMessage, RecapMessage, ExerciseMessage) possède son propre état local (`useState`) et appelle directement le context. Ils ne reçoivent pas de callbacks par props, ce qui les rend autonomes mais couplés au context.

### Déploiement mixte
Le frontend React appelle un backend déployé sur Render. La constante `API_URL` est codée en dur dans `Sidebar.jsx` et `MessageItem.jsx`. En développement local, il faut pointer vers `http://localhost:8000`.

---

## 8. Démarrage Rapide

### Backend (Python 3.11+)
```bash
cd backend
pip install -r requirements.txt
python main.py
# → http://localhost:8000
# → http://localhost:8000/docs  (Swagger UI)
```

### Frontend (Node 18+)
```bash
cd pedabot-react
npm install
npm run dev
# → http://localhost:5173
```

### Routes API disponibles

| Méthode | Route | Description |
|---------|-------|-------------|
| GET | `/` | Health check |
| POST | `/api/analyze` | Analyse un cours → sections + syntaxe |
| POST | `/api/generate` | Génère des exercices selon les paramètres |
| POST | `/api/deepen` | Génère une version approfondie d'un exercice |

---

*Généré par analyse architecturale — PédaBot v1.0*
