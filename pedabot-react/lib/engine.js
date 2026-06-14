// ══════════════════════════════════════════════════════════════
//  PédaBot — Moteur NLP JavaScript (port de engine.py Python)
//  40 patterns de détection, génération d'exercices Bloom
// ══════════════════════════════════════════════════════════════

// ── Helpers ──────────────────────────────────────────────────

const ART = String.raw`(?:[UuDd](?:n|ne|es)\s+|[Ll](?:e|a|es)\s+|[Ll]['']|[Cc](?:e(?:tte|t)?|es)\s+)`;

function splitSentences(text) {
  return text.split(/[.!?\n;]+/).map(s => s.trim()).filter(s => s.length >= 15);
}

function cleanKeyword(kw) {
  kw = kw.trim().replace(/[,.;:!?]+$/, '').trim();
  kw = kw.replace(/\s+/g, ' ');
  kw = kw.replace(/^(?:un|une|le|la|l['']|les|des|du|d['']|ce|cette|ces)\s+/i, '');
  kw = kw.replace(/^(?:autre|autres|principal|principale|seul|seule|même|premier|première)\s+/i, '');
  const words = kw.split(' ');
  if (words.length > 5) kw = words.slice(0, 5).join(' ');
  return kw.trim();
}

function secTitleFrom(text) {
  return (text.split('.')[0] || '').slice(0, 40).trim();
}

// ══════════════════════════════════════════════════════════════
//  MOTEUR 1 — DÉTECTION DES SECTIONS
// ══════════════════════════════════════════════════════════════

export function detectSections(txt) {
  const lines = txt.split('\n');
  const PATS = [
    [/^(I{1,3}V?|VI{0,3}|IX|X{1,3})[.)]\s+(.+)/i, 0, 1],
    [/^(\d{1,2})[.)]\s+([A-ZÀÂÉÈÊÙÛÇ].{2,})/, 0, 1],
    [/^([A-Z])[.)]\s+([A-ZÀÂÉÈÊÙÛÇ].{2,})/, 0, 1],
    [/^(Chapitre|Partie|Section)\s+\d[^:]*[:\-]\s*(.+)/i, 0, 1],
    [/^#{1,3}\s+(.+)/, null, 0],
  ];

  const secs = [];
  let cur = null;
  let body = '';

  for (const line of lines) {
    const l = line.trim();
    if (!l) continue;
    let hit = false;
    for (const [pattern, nIdx, tIdx] of PATS) {
      const m = l.match(pattern);
      if (m) {
        if (cur) { cur.content = body.trim(); secs.push(cur); }
        const num = nIdx !== null ? (m[nIdx + 1] || '') : '';
        const title = (m[tIdx + 1] || l).trim();
        cur = { num, title, content: '' };
        body = '';
        hit = true;
        break;
      }
    }
    if (!hit && cur) body += ' ' + l;
  }
  if (cur) { cur.content = body.trim(); secs.push(cur); }
  return secs.slice(0, 7);
}

// ══════════════════════════════════════════════════════════════
//  MOTEUR 2 — DÉTECTION DE SYNTAXE
// ══════════════════════════════════════════════════════════════

export function detectLang(txt) {
  const t = txt.toLowerCase();
  const algoCount = (t.match(/tant que|répéter|jusqu'à|début|fin|écrire|lire|algorithme|pour.*faire/g) || []).length;
  const pyCount   = (t.match(/def |print\(|import |while |for .+in|if __name__|range\(/g) || []).length;
  const jsCount   = (t.match(/function |console\.|const |let |var |=>/g) || []).length;
  if (algoCount >= pyCount && algoCount >= jsCount) return ['algo', 'Algorithmique'];
  if (pyCount >= jsCount) return ['python', 'Python'];
  return ['javascript', 'JavaScript'];
}

export function detectCourseName(txt) {
  const patterns = [
    /(?:Cours|Course)\s*(?::\s*|–\s*|-\s*|—\s*)(.+)/i,
    /(?:Leçon|Lecon)\s*\d*\s*(?::\s*|–\s*|-\s*|—\s*)(.+)/i,
    /(?:Chapitre|Chapter)\s*\d*\s*(?::\s*|–\s*|-\s*|—\s*)(.+)/i,
    /(?:UE|Unité\s+d['']Enseignement)\s*\d*\s*(?::\s*|–\s*|-\s*|—\s*)(.+)/i,
    /(?:Module)\s*\d*\s*(?::\s*|–\s*|-\s*|—\s*)(.+)/i,
    /(?:Thème|Theme)\s*\d*\s*(?::\s*|–\s*|-\s*|—\s*)(.+)/i,
    /(?:Séquence|Sequence)\s*\d*\s*(?::\s*|–\s*|-\s*|—\s*)(.+)/i,
  ];
  for (const p of patterns) {
    const m = txt.match(p);
    if (m) {
      let name = m[1].trim().replace(/<[^>]+>/g, '').trim();
      if (name.length > 80) name = name.slice(0, 80).replace(/\s\w+$/, '') + '…';
      if (name.length >= 3) return name;
    }
  }
  return '';
}

// ══════════════════════════════════════════════════════════════
//  PATTERNS 1-24 — DÉTECTION TEXTUELLE
// ══════════════════════════════════════════════════════════════

function makeDetector(markers, questionFn, maxWords = 6) {
  return function(text) {
    const sentences = splitSentences(text);
    const results = [], seen = new Set();
    for (const s of sentences) {
      for (const marker of markers) {
        const re = new RegExp(String.raw`(${ART}[\wéèêëàâùûîïôœç'']+(?:\s+[\wéèêëàâùûîïôœç'']+){0,3})\s+(?:${marker})`, 'i');
        const m = s.match(re);
        if (m) {
          const kw = cleanKeyword(m[1]);
          if (kw.split(' ').length >= 1 && kw.split(' ').length <= maxWords && !seen.has(kw.toLowerCase())) {
            seen.add(kw.toLowerCase());
            results.push({ keyword: kw, question: questionFn(kw), sentence: s });
          }
          break;
        }
      }
    }
    return results;
  };
}

export const detectDefinitions = (function() {
  const MARKERS_BEFORE = [
    String.raw`est\s+un(?:e)?\b`, String.raw`est\s+l(?:e|a|[''])\b`, String.raw`est\s+des\b`,
    String.raw`est\s+définie?\s+comme`, String.raw`est\s+appelée?`, String.raw`est\s+considérée?\s+comme`,
    String.raw`représente`, String.raw`désigne`, String.raw`constitue`, String.raw`signifie`,
    String.raw`correspond(?:ent)?\s+à`, String.raw`consiste\s+(?:à|en)`, String.raw`se\s+définit\s+comme`,
    String.raw`(?:permet|sert)\s+(?:à|de)`, String.raw`a\s+pour\s+(?:rôle|but|objectif|fonction)`,
  ];
  return makeDetector(MARKERS_BEFORE, kw => {
    const vowel = 'aeéèêëiïîoôuùûyh'.includes((kw[0] || '').toLowerCase());
    return `Qu'est-ce que ${vowel ? "l'" : "le "}${kw} ?`;
  });
})();

export const detectCauses = makeDetector([
  String.raw`(?:a\s+été|est)\s+causée?\s+par`, String.raw`est\s+(?:dû|due)\s+à`,
  String.raw`résulte\s+de`, String.raw`s['']explique\s+par`, String.raw`provient\s+de`,
  String.raw`est\s+provoquée?\s+par`, String.raw`découle\s+de`,
], kw => `Quelles sont les causes de ${kw.toLowerCase()} ?`);

export const detectConsequences = makeDetector([
  String.raw`entraîne`, String.raw`provoque`, String.raw`conduit\s+à`,
  String.raw`a\s+pour\s+(?:effet|conséquence|résultat|impact)`,
  String.raw`engendre`, String.raw`génère`, String.raw`se\s+traduit\s+par`,
], kw => `Quelles sont les conséquences de ${kw.toLowerCase()} ?`);

export const detectCaracteristiques = makeDetector([
  String.raw`se\s+caractérise\s+par`, String.raw`est\s+caractérisée?\s+par`,
  String.raw`possède`, String.raw`présente\s+(?:les?|des|plusieurs)`,
  String.raw`a\s+pour\s+(?:propriété|caractéristique|attribut)`,
  String.raw`se\s+distingue\s+par`,
], kw => `Quelles sont les caractéristiques de ${kw.toLowerCase()} ?`);

export const detectFonctions = makeDetector([
  String.raw`sert\s+à`, String.raw`permet\s+de`,
  String.raw`a\s+pour\s+(?:fonction|rôle|but|mission|objectif)`,
  String.raw`joue\s+(?:le|un)\s+rôle\s+de`, String.raw`vise\s+à`,
  String.raw`est\s+utilisée?\s+pour`, String.raw`est\s+destinée?\s+à`,
], kw => `À quoi sert ${kw.toLowerCase()} ?`);

export const detectExemples = makeDetector([
  String.raw`par\s+exemple`, String.raw`tels?\s+que`, String.raw`notamment`,
  String.raw`on\s+peut\s+citer`, String.raw`incluent?`, String.raw`parmi\s+(?:les|eux|elles)`,
], kw => `Citez des exemples de ${kw.toLowerCase()}.`);

export const detectEtapes = (function() {
  const markers = [
    String.raw`se\s+déroule\s+en`, String.raw`comporte\s+(?:\d+|plusieurs)\s+(?:étapes?|phases?)`,
    String.raw`comprend\s+(?:\d+|plusieurs)\s+(?:étapes?|phases?)`,
    String.raw`se\s+compose\s+de\s+(?:\d+|plusieurs)\s+(?:étapes?|phases?)`,
  ];
  return function(text) {
    const results = makeDetector(markers, kw => `Quelles sont les étapes de ${kw.toLowerCase()} ?`)(text);
    return results;
  };
})();

export const detectAvantages = (function() {
  return function(text) {
    const sentences = splitSentences(text);
    const hasAvantage    = sentences.some(s => /avantage|point\s+fort|atout|bénéfice|intérêt/i.test(s));
    const hasInconvenient = sentences.some(s => /inconvénient|risque|limite|point\s+faible|cependant|néanmoins|toutefois/i.test(s));
    if (!hasAvantage && !hasInconvenient) return [];
    const results = [], seen = new Set();
    const markers = [String.raw`l['']avantage\s+(?:est|de)`, String.raw`l['']inconvénient`, String.raw`le\s+point\s+fort`];
    for (const s of sentences) {
      for (const marker of markers) {
        const re = new RegExp(String.raw`(?:${marker})\s+(?:du|de\s+la|de\s+l['']|des|de)\s+(.+?)(?:\s+est|\s*,|\s*:)`, 'i');
        const m = s.match(re);
        if (m) {
          const kw = cleanKeyword(m[1]);
          if (kw.split(' ').length <= 6 && !seen.has(kw.toLowerCase())) {
            seen.add(kw.toLowerCase());
            const q = hasAvantage && hasInconvenient ? 'Citez un avantage et un inconvénient' : hasAvantage ? 'Quels sont les avantages' : 'Quelles sont les limites';
            results.push({ keyword: kw, question: `${q} de ${kw.toLowerCase()} ?`, sentence: s });
          }
          break;
        }
      }
      if (results.length) break;
    }
    return results;
  };
})();

export const detectClassifications = makeDetector([
  String.raw`il\s+existe\s+(?:\d+|plusieurs|\w+)\s+(?:types|catégories)`,
  String.raw`on\s+distingue`, String.raw`se\s+divise\s+en`, String.raw`se\s+répartit\s+en`,
  String.raw`peut\s+être\s+classée?\s+en`,
], kw => `Quels sont les différents types de ${kw.toLowerCase()} ?`);

export const detectConditions = makeDetector([
  String.raw`nécessite`, String.raw`requiert`, String.raw`implique`, String.raw`suppose`,
  String.raw`il\s+faut\s+(?:que|un|une|des)`, String.raw`est\s+nécessaire`,
], kw => `Quelles sont les conditions pour ${kw.toLowerCase()} ?`);

export const detectFormules = makeDetector([
  String.raw`se\s+calcule\s+par`, String.raw`s['']exprime\s+par`,
  String.raw`la\s+formule\s+est`, String.raw`est\s+donnée?\s+par`,
], kw => `Quelle est la formule / règle de ${kw.toLowerCase()} ?`);

export const detectLocalisations = makeDetector([
  String.raw`se\s+situe`, String.raw`se\s+trouve`, String.raw`est\s+localisée?`,
  String.raw`au\s+(?:nord|sud|est|ouest)\s+de`, String.raw`s['']étend\s+sur`,
], kw => `Où se situe ${kw.toLowerCase()} ?`);

export const detectCompositions = makeDetector([
  String.raw`est\s+composée?\s+de`, String.raw`comprend`, String.raw`contient`,
  String.raw`se\s+compose\s+de`, String.raw`est\s+constituée?\s+de`, String.raw`regroupe`,
], kw => `De quoi est composé(e) ${kw.toLowerCase()} ?`);

export const detectSynonymes = makeDetector([
  String.raw`aussi\s+appelée?`, String.raw`également\s+nommée?`,
  String.raw`autrement\s+dit`, String.raw`c['']est-à-dire`, String.raw`synonyme\s+de`,
], kw => `Quels sont les synonymes / autres termes pour ${kw.toLowerCase()} ?`);

export const detectObjectifs = makeDetector([
  String.raw`a\s+pour\s+objectif`, String.raw`vise\s+à`,
  String.raw`dans\s+le\s+but\s+de`, String.raw`afin\s+de`, String.raw`cherche\s+à`,
], kw => `Quel est l'objectif de ${kw.toLowerCase()} ?`);

export function detectDates(text) {
  const sentences = splitSentences(text);
  const results = [], seen = new Set();
  for (const s of sentences) {
    const dm = s.match(/\b(\d{4})\b/);
    if (dm) {
      const before = s.slice(0, s.indexOf(dm[0])).trim();
      const kw = cleanKeyword(before);
      if (kw.split(' ').length >= 2 && kw.split(' ').length <= 8 && !seen.has(kw.toLowerCase())) {
        seen.add(kw.toLowerCase());
        results.push({ keyword: kw, question: `En quelle année ${kw.toLowerCase()} a-t-il eu lieu ?`, sentence: s, date: dm[1] });
      }
    }
  }
  return results;
}

export function detectActeurs(text) {
  const sentences = splitSentences(text);
  const results = [], seen = new Set();
  const markers = [
    /selon\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)/,
    /d['']après\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)/,
    /([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\s+a\s+(?:dit|écrit|proposé|découvert)/,
  ];
  for (const s of sentences) {
    for (const re of markers) {
      const m = s.match(re);
      if (m && m[1].length > 3 && !seen.has(m[1].toLowerCase())) {
        seen.add(m[1].toLowerCase());
        results.push({ keyword: m[1], question: `Qui a découvert / proposé ce concept ?`, sentence: s });
        break;
      }
    }
  }
  return results;
}

export function detectChiffres(text) {
  const sentences = splitSentences(text);
  const results = [], seen = new Set();
  const markers = [/représente\s+(\d+(?:[.,]\d+)?\s*(?:%|pourcents?))/, /atteint\s+(\d+(?:[.,]\d+)?)/, /mesure\s+(\d+(?:[.,]\d+)?)/];
  for (const s of sentences) {
    for (const re of markers) {
      const m = s.match(re);
      if (m) {
        const re2 = new RegExp(String.raw`(${ART}[\wéèêëàâùûîïôœç'']+(?:\s+[\wéèêëàâùûîïôœç'']+){0,3})\s+(?:représente|atteint|mesure)`, 'i');
        const m2 = s.match(re2);
        const kw = m2 ? cleanKeyword(m2[1]) : 'cette valeur';
        if (!seen.has(kw.toLowerCase())) {
          seen.add(kw.toLowerCase());
          results.push({ keyword: kw, question: `Quel chiffre/pourcentage correspond à ${kw.toLowerCase()} ?`, sentence: s });
        }
        break;
      }
    }
  }
  return results;
}

export function detectAbreviations(text) {
  const sentences = text.split(/[.!?\n;]+/).map(s => s.trim()).filter(s => s.length >= 10);
  const results = [], seen = new Set();
  for (const s of sentences) {
    const m = s.match(/\b([A-Z0-9]{2,10})\s+\(([^()]{5,})\)/);
    if (m && !seen.has(m[1].toLowerCase())) {
      seen.add(m[1].toLowerCase());
      results.push({ keyword: m[1], question: `Que signifie l'acronyme ${m[1]} ?`, sentence: s });
    }
  }
  return results;
}

export function detectExceptions(text) {
  const sentences = splitSentences(text);
  const results = [], seen = new Set();
  const markers = [/\bsauf\b/i, /\bexcepté\b/i, /à\s+l['']exception\s+de/i, /attention/i, /il\s+faut\s+noter\s+que/i];
  for (const s of sentences) {
    for (const re of markers) {
      if (re.test(s)) {
        const kw = 'cette règle';
        if (!seen.has(kw)) {
          seen.add(kw);
          results.push({ keyword: kw, question: `Quelle est l'exception concernant ${kw} ?`, sentence: s });
        }
        break;
      }
    }
  }
  return results;
}

export function detectRemarques(text) {
  const sentences = text.split(/[.!?\n;]+/).map(s => s.trim()).filter(s => s.length >= 15);
  const results = [], seen = new Set();
  for (const s of sentences) {
    const m = s.match(/\b(NB|N\.B|Remarque|Attention|Important|À noter)\s*[:.-]*\s*(.+)/i);
    if (m) {
      const kw = 'cette règle';
      if (!seen.has(kw)) {
        seen.add(kw);
        results.push({ keyword: kw, question: `Quelle information importante (NB/Attention) concerne ${kw} ?`, sentence: s });
      }
    }
  }
  return results;
}

export function detectTraductions(text) {
  const sentences = text.split(/[\n;]+/).map(s => s.trim()).filter(s => s.length >= 5);
  const results = [], seen = new Set();
  for (const s of sentences) {
    let kw = null;
    if (/\b(?:écrire|afficher)\b/i.test(s) && /\b(?:printf|console\.log|print)\b/i.test(s))
      kw = "une instruction d'écriture (ex: AFFICHER/ECRIRE)";
    else if (/\b(?:lire|saisir)\b/i.test(s) && /\b(?:scanf|input|prompt|cin)\b/i.test(s))
      kw = "une instruction de lecture (ex: LIRE)";
    if (kw && !seen.has(kw)) {
      seen.add(kw);
      results.push({ keyword: kw, question: `Comment traduit-on ${kw} en langage code ?`, sentence: s });
    }
  }
  return results;
}

export function detectTableaux(text) {
  const sentences = text.split(/[\n;]+/).map(s => s.trim()).filter(s => s.length >= 4);
  const results = [], seen = new Set();
  for (const s of sentences) {
    const m = s.match(/(%[a-zA-Z])\s*(?:[|:→-]*\s*)([a-zA-Zéèàâêôûîïç_]+(?:\s+[a-zA-Zéèàâêôûîïç_]+)*)/);
    if (m && !/printf|scanf/i.test(s)) {
      const kw = m[1];
      if (!seen.has(kw)) {
        seen.add(kw);
        results.push({ keyword: kw, question: `Quel format utilise-t-on pour afficher/lire un(e) : ${m[2].toLowerCase()} ?`, sentence: s });
      }
    }
  }
  return results;
}

export function detectStructures(text) {
  const sentences = text.split(/[.!?\n;]+/).map(s => s.trim()).filter(s => s.length >= 10);
  const results = [], seen = new Set();
  for (const s of sentences) {
    const m = s.match(/(?:structure|syntaxe)\s+(?:générale\s+)?(?:de\s+la|d['']une|de\s+l['']|du|de)\s+(?:requête|boucle|fonction|instruction\s+)?([A-Z0-9_]+(?:\s+[A-Z0-9_]+)*|[a-zA-Z0-9_]+)\b/i)
           || s.match(/([a-zA-Z0-9_]+(?:\s+[a-zA-Z0-9_]+)*)\s+(?:s['']écrit|se\s+déclare)/i);
    if (m) {
      const kw = cleanKeyword(m[1]);
      if (kw.length > 1 && !seen.has(kw.toLowerCase())) {
        seen.add(kw.toLowerCase());
        results.push({ keyword: kw, question: `Quelle est la structure de la syntaxe de ${kw} ?`, sentence: s });
      }
    }
  }
  return results;
}

// ══════════════════════════════════════════════════════════════
//  PATTERNS 26-31 — BLOCS DE SYNTAXE ALGORITHMIQUE
// ══════════════════════════════════════════════════════════════

export function detectSyntaxePour(text) {
  const pats = [/POUR\s+\w+\s+DE\s+.+\s+(?:À|A)\s+.+\s+FAIRE/i, /for\s+\w+\s+in\s+range\s*\(/i, /for\s*\(let\s+\w+\s*=/i, /FIN\s+POUR/i];
  if (pats.some(p => p.test(text))) return [{ keyword: 'boucle POUR', question: 'Écrire un algorithme utilisant une boucle POUR', sentence: text.slice(0, 200) }];
  if (/boucle\s+pour|boucle\s+for|répétition\s+fixe|compteur|nombre\s+de\s+fois/i.test(text.split('.')[0]))
    return [{ keyword: 'boucle POUR', question: 'Écrire un algorithme utilisant une boucle POUR', sentence: text.slice(0, 200) }];
  return [];
}

export function detectSyntaxeTantque(text) {
  const pats = [/TANT\s+QUE\s+.+\s+FAIRE/i, /FIN\s+TANT\s+QUE/i, /while\s+\w+.*:/i, /while\s*\(.+\)\s*\{/i];
  if (pats.some(p => p.test(text))) return [{ keyword: 'boucle TANT QUE', question: 'Écrire un algorithme utilisant une boucle TANT QUE', sentence: text.slice(0, 200) }];
  if (/tant\s+que|while|boucle\s+condition|répétition\s+condition/i.test(text.split('.')[0]))
    return [{ keyword: 'boucle TANT QUE', question: 'Écrire un algorithme utilisant une boucle TANT QUE', sentence: text.slice(0, 200) }];
  return [];
}

export function detectSyntaxeRepeter(text) {
  const pats = [/RÉPÉTER/i, /JUSQU['']À/i, /do\s*\{/i, /\}\s*while\s*\(/i];
  const matched = pats.filter(p => p.test(text)).length;
  if (matched >= 1) {
    if (/répéter|jusqu['']à|do.while|post.condition/i.test(text.split('.')[0]) || matched >= 2)
      return [{ keyword: "boucle RÉPÉTER JUSQU'À", question: "Écrire un algorithme utilisant une boucle RÉPÉTER JUSQU'À", sentence: text.slice(0, 200) }];
  }
  return [];
}

export function detectSyntaxeSi(text) {
  const pats = [/SI\s+.+\s+ALORS/i, /FIN\s+SI/i, /SINON\s+SI/i, /if\s+.+:/i, /elif\s+/i, /if\s*\(.+\)\s*\{/i, /else\s+if\s*\(/i];
  if (pats.some(p => p.test(text))) return [{ keyword: 'structure SI/SINON', question: 'Écrire un algorithme utilisant une alternative SI/SINON', sentence: text.slice(0, 200) }];
  if (/alternative|si\s+sinon|if\s+else|structure\s+conditionnelle|prise\s+de\s+décision/i.test(text.split('.')[0]))
    return [{ keyword: 'structure SI/SINON', question: 'Écrire un algorithme utilisant une alternative SI/SINON', sentence: text.slice(0, 200) }];
  return [];
}

export function detectSyntaxeFonction(text) {
  const pats = [/FONCTION\s+\w+\s*\(/i, /PROCÉDURE\s+\w+\s*\(/i, /PROCEDURE\s+\w+\s*\(/i, /RETOURNER\s+/i, /def\s+\w+\s*\(/i, /function\s+\w+\s*\(/i];
  if (pats.some(p => p.test(text))) return [{ keyword: 'fonction/procédure', question: 'Écrire et appeler une fonction', sentence: text.slice(0, 200) }];
  if (/fonction|procédure|sous-programme|def |modularité|retourner/i.test(text.split('.')[0]))
    return [{ keyword: 'fonction/procédure', question: 'Écrire et appeler une fonction', sentence: text.slice(0, 200) }];
  return [];
}

export function detectSyntaxeTableau(text) {
  const pats = [/TABLEAU\s*\[/i, /\w+\s*\[\s*\d+\s*\.\.\s*\d*/i, /\w+\s*\[\s*i\s*\]/i, /\.append\s*\(/i, /\.push\s*\(/i, /new\s+Array\s*\(/i];
  if (pats.some(p => p.test(text))) return [{ keyword: 'tableau/liste', question: 'Écrire un algorithme utilisant un tableau', sentence: text.slice(0, 200) }];
  if (/\btableau\b|array|\bliste\b|indice|index|parcours\s+de/i.test(text.split('.')[0]))
    return [{ keyword: 'tableau/liste', question: 'Écrire un algorithme utilisant un tableau', sentence: text.slice(0, 200) }];
  return [];
}

// ══════════════════════════════════════════════════════════════
//  PATTERNS 32-40 — ANALYSE, COMPARAISON, RÈGLES
// ══════════════════════════════════════════════════════════════

export function detectComparaison(text) {
  const markers = [/contrairement\s+à/i, /à\s+l['']opposé\s+de/i, /tandis\s+que/i, /alors\s+que/i, /différence\s+entre/i, /comparé\s+à/i, /\bvs\b|\bversus\b/i];
  for (const re of markers) {
    const m = text.match(re);
    if (m) {
      const before = text.slice(0, m.index).trim().split(/\s+/).slice(-5).join(' ').replace(/[.,;:]+$/, '');
      const kw = cleanKeyword(before) || secTitleFrom(text);
      return [{ keyword: cleanKeyword(kw), question: 'Comparez les deux éléments mentionnés.', sentence: text.slice(0, 300) }];
    }
  }
  return [];
}

export function detectErreurPiege(text) {
  const markers = [/erreur\s+(?:courante|fréquente|typique|classique)/i, /piège\s+(?:fréquent|courant)/i, /attention\s+à\s+ne\s+pas/i, /ne\s+pas\s+confondre/i];
  for (const re of markers) {
    const m = text.match(re);
    if (m) {
      const after = text.slice(m.index + m[0].length, m.index + m[0].length + 80).trim().split('.')[0];
      const kw = cleanKeyword(after.slice(0, 40)) || 'cette règle';
      return [{ keyword: kw, question: "Identifiez et corrigez l'erreur décrite.", sentence: text.slice(0, 300) }];
    }
  }
  return [];
}

export function detectTraceExecution(text) {
  const markers = [/tableau\s+de\s+(?:trace|valeurs|suivi)/i, /trace\s+d['']exécution/i, /déroulement\s+pas\s+à\s+pas/i, /valeurs\s+successives/i, /après\s+exécution/i];
  if (markers.some(re => re.test(text))) return [{ keyword: "trace d'exécution", question: 'Complétez le tableau de trace.', sentence: text.slice(0, 300) }];
  return [];
}

export function detectEntreeSortie(text) {
  const markers = [/prend\s+en\s+entrée/i, /retourne\s+(?:en\s+sortie|une\s+valeur)/i, /données?\s+d['']entrée/i, /paramètres?\s+d['']entrée/i, /entrée\s*:/i, /sortie\s*:/i];
  if (markers.some(re => re.test(text))) return [{ keyword: "interface de la fonction", question: 'Identifiez les entrées et sorties.', sentence: text.slice(0, 300) }];
  return [];
}

export function detectPreconditions(text) {
  const markers = [/précondition/i, /postcondition/i, /à\s+condition\s+que/i, /garantit\s+que/i, /contrat\s+(?:de|d[''])/i];
  if (markers.some(re => re.test(text))) return [{ keyword: 'préconditions/postconditions', question: 'Énoncez les préconditions et postconditions.', sentence: text.slice(0, 300) }];
  return [];
}

export function detectConversionLangage(text) {
  const hasAlgo = /POUR\s+\w+\s+DE|TANT\s+QUE|RÉPÉTER|FONCTION\s+\w+\s*\(|RETOURNER/.test(text);
  const hasPy   = /\bdef\s+\w+\s*\(|\bfor\s+\w+\s+in\s+|\bwhile\s+/.test(text);
  const hasJs   = /\bfunction\s+\w+\s*\(|console\.log\s*\(|\bconst\b|\blet\b/.test(text);
  const explicit = /équivalent\s+en\s+(?:Python|JavaScript|algorithmique)|s['']écrit\s+en\s+Python|se\s+traduit\s+en\s+(?:JavaScript|Python)/i.test(text);
  if (explicit || (hasAlgo && (hasPy || hasJs)))
    return [{ keyword: 'traduction langage', question: "Traduisez dans l'autre langage.", sentence: text.slice(0, 300) }];
  return [];
}

export function detectComplexite(text) {
  const markers = [/complexité\s+(?:en\s+temps|en\s+espace|temporelle|algorithmique)?/i, /O\s*\(\s*(?:n²?|n\^2|log\s*n|1|n\s*log\s*n)\s*\)/i, /plus\s+(?:efficace|optimal|rapide)\s+que/i, /nombre\s+d['']opérations/i];
  if (markers.some(re => re.test(text))) return [{ keyword: 'complexité algorithmique', question: 'Analysez la complexité et proposez une amélioration.', sentence: text.slice(0, 300) }];
  return [];
}

export function detectRegleAbsolue(text) {
  const markers = [/il\s+faut\s+toujours/i, /on\s+ne\s+doit\s+(?:jamais|pas)/i, /principe\s+fondamental/i, /règle\s+(?:d['']or|de\s+base|fondamentale)/i, /toujours\s+(?:vérifier|s['']assurer|initialiser)/i];
  for (const re of markers) {
    const m = text.match(re);
    if (m) {
      const after = text.slice(m.index + m[0].length, m.index + m[0].length + 80).trim().split('.')[0];
      const kw = cleanKeyword(after.slice(0, 40)) || 'cette règle';
      return [{ keyword: kw, question: 'Énoncez la règle et donnez un contre-exemple.', sentence: text.slice(0, 300) }];
    }
  }
  return [];
}

export function detectSchema(text) {
  const markers = [/(?:le|un)\s+schéma\s+(?:montre|représente)/i, /comme\s+le\s+montre\s+(?:la\s+figure|le\s+diagramme)/i, /\borganigramme\b/i, /diagramme\s+(?:de|d['']|des)/i];
  if (markers.some(re => re.test(text))) return [{ keyword: 'schéma/organigramme', question: 'Décrivez ou reproduisez le schéma.', sentence: text.slice(0, 300) }];
  return [];
}

// ══════════════════════════════════════════════════════════════
//  DISPATCHER — Meilleur pattern pour une section
// ══════════════════════════════════════════════════════════════

function detectBestPattern(sec) {
  const text = `${sec.title}. ${sec.content}`;

  // Priorité 1 : syntaxe algorithmique
  for (const [name, fn] of [
    ['syntaxe_pour', detectSyntaxePour], ['syntaxe_tantque', detectSyntaxeTantque],
    ['syntaxe_repeter', detectSyntaxeRepeter], ['syntaxe_si', detectSyntaxeSi],
    ['syntaxe_fonction', detectSyntaxeFonction], ['syntaxe_tableau', detectSyntaxeTableau],
  ]) {
    const data = fn(text);
    if (data.length) return [name, data];
  }

  // Priorité 2 : analytiques
  for (const [name, fn] of [
    ['comparaison', detectComparaison], ['erreur_piege', detectErreurPiege],
    ['trace_execution', detectTraceExecution], ['entree_sortie', detectEntreeSortie],
    ['preconditions', detectPreconditions], ['conversion_langage', detectConversionLangage],
    ['complexite', detectComplexite], ['regle_absolue', detectRegleAbsolue],
    ['schema', detectSchema],
  ]) {
    const data = fn(text);
    if (data.length) return [name, data];
  }

  // Priorité 3 : textuels classiques
  for (const [name, fn] of [
    ['definition', detectDefinitions], ['cause', detectCauses],
    ['consequence', detectConsequences], ['etape', detectEtapes],
    ['caracteristique', detectCaracteristiques], ['fonction', detectFonctions],
    ['exemple', detectExemples], ['date', detectDates],
    ['avantage', detectAvantages], ['classification', detectClassifications],
    ['condition', detectConditions], ['acteur', detectActeurs],
    ['formule', detectFormules], ['chiffre', detectChiffres],
    ['localisation', detectLocalisations], ['composition', detectCompositions],
    ['synonyme', detectSynonymes], ['exception', detectExceptions],
    ['abreviation', detectAbreviations], ['tableau', detectTableaux],
    ['remarque', detectRemarques], ['traduction', detectTraductions],
    ['objectif', detectObjectifs], ['structure', detectStructures],
  ]) {
    const data = fn(text);
    if (data.length) return [name, data];
  }
  return [null, []];
}

// ══════════════════════════════════════════════════════════════
//  GÉNÉRATEUR D'EXERCICES SYNTAXE (Patterns 26-31)
// ══════════════════════════════════════════════════════════════

function makeSyntaxeExercise(sec, level, patType, isAlgo, isPy) {
  const META = {
    syntaxe_pour: {
      nom: 'Boucle POUR',
      trous_algo: "Variable i, N, somme : Entier\nDébut\n   Lire(N)\n   somme ← __\n   Pour i de __ à N Faire\n      somme ← somme + __\n   FinPour\n   Écrire(somme)\nFin",
      trous_py:   "N = int(input())\ntotal = __\nfor i in range(__, __ + 1):\n    total += __\nprint(total)",
      trous_js:   "let total = __;\nfor (let i = __; i <= N; i++) {\n    total += __;\n}\nconsole.log(total);",
      scenario_algo: { titre: 'Calculer la somme des entiers', enonce: "Écrire un algorithme qui calcule la somme des entiers de 1 à N.", code: "Variable i, N, somme : Entier\nDébut\n   Écrire(\"Entrer N :\")\n   Lire(N)\n   somme ← 0\n   Pour i de 1 à N Faire\n      somme ← somme + i\n   FinPour\n   Écrire(\"Somme = \", somme)\nFin" },
      scenario_py:  { titre: 'Calculer la somme des entiers', enonce: "Écrire une fonction Python qui calcule la somme des entiers de 1 à N.", code: "def somme_entiers(N):\n    total = 0\n    for i in range(1, N + 1):\n        total += i\n    return total\nN = int(input('Entrer N : '))\nprint('Somme =', somme_entiers(N))" },
      scenario_js:  { titre: 'Table de multiplication', enonce: "Écrire une fonction JavaScript qui affiche la table de multiplication.", code: "function tableMultiplication(n) {\n  for (let i = 1; i <= 10; i++) {\n    console.log(`${n} × ${i} = ${n * i}`);\n  }\n}\ntableMultiplication(parseInt(prompt('Entier :')));" },
    },
    syntaxe_tantque: {
      nom: 'Boucle TANT QUE',
      trous_algo: "Variable n, somme : Entier\nDébut\n   somme ← 0\n   Lire(n)\n   Tant que __ Faire\n      somme ← somme + n\n      __\n   FinTantQue\n   Écrire(somme)\nFin",
      trous_py:   "somme = 0\nn = int(input())\nwhile __:\n    somme += n\n    n = int(input())\nprint(somme)",
      trous_js:   "let somme = 0, n;\nn = parseInt(prompt());\nwhile (__) {\n    somme += n;\n    n = parseInt(__);\n}\nconsole.log(somme);",
      scenario_algo: { titre: "Lire jusqu'à 0", enonce: "Écrire un algorithme qui lit des entiers et s'arrête quand l'utilisateur saisit 0.", code: "Variable n, somme : Entier\nDébut\n   somme ← 0\n   Lire(n)\n   Tant que n != 0 Faire\n      somme ← somme + n\n      Lire(n)\n   FinTantQue\n   Écrire(\"Somme = \", somme)\nFin" },
      scenario_py:  { titre: "Lire jusqu'à 0", enonce: "Écrire un programme Python qui lit des entiers jusqu'à la saisie de 0.", code: "somme = 0\nn = int(input('Entier (0 pour arrêter) : '))\nwhile n != 0:\n    somme += n\n    n = int(input('Entier : '))\nprint('Somme =', somme)" },
      scenario_js:  { titre: 'Deviner un nombre', enonce: "Écrire un programme JavaScript où l'utilisateur devine un nombre secret.", code: "const secret = 42;\nlet essai;\nwhile (essai !== secret) {\n  essai = parseInt(prompt('Devinez :'));\n  if (essai < secret) console.log('Trop petit !');\n  else if (essai > secret) console.log('Trop grand !');\n}\nconsole.log('Bravo !');" },
    },
    syntaxe_repeter: {
      nom: "Boucle RÉPÉTER JUSQU'À",
      trous_algo: "Variable n : Entier\nDébut\n   __\n      Écrire(\"Saisir un positif :\")\n      Lire(n)\n   __ (n > 0)\n   Écrire(n)\nFin",
      trous_py:   "while __:\n    n = int(input('Saisir un positif : '))\n    if n > 0:\n        __\n    print('Invalide')\nprint(n)",
      trous_js:   "let n;\ndo {\n  n = parseInt(prompt('Saisir un positif :'));\n} while (__);\nconsole.log(n);",
      scenario_algo: { titre: 'Validation de saisie', enonce: "Écrire un algorithme qui force l'utilisateur à saisir un entier strictement positif.", code: "Variable n : Entier\nDébut\n   Répéter\n      Écrire(\"Saisir un entier positif :\")\n      Lire(n)\n   Jusqu'à (n > 0)\n   Écrire(\"Valeur acceptée : \", n)\nFin" },
      scenario_py:  { titre: 'Validation de saisie', enonce: "Python n'a pas de do-while natif. Écrire l'équivalent avec while True et break.", code: "while True:\n    n = int(input('Saisir un entier positif : '))\n    if n > 0:\n        break\n    print('Valeur invalide !')\nprint('Valeur acceptée :', n)" },
      scenario_js:  { titre: 'Menu interactif', enonce: "Écrire un menu interactif en JavaScript avec do...while.", code: "let choix;\ndo {\n  choix = parseInt(prompt('1-Ajouter  2-Supprimer  0-Quitter'));\n  if (choix === 1) console.log('Ajout...');\n  else if (choix === 2) console.log('Suppression...');\n} while (choix !== 0);\nconsole.log('Au revoir !');" },
    },
    syntaxe_si: {
      nom: 'Structure SI / SINON',
      trous_algo: "Variable note : Réel\nDébut\n   Lire(note)\n   __ note >= 10 __ \n      Écrire(\"Admis\")\n   __\n      Écrire(\"Échec\")\n   FinSi\nFin",
      trous_py:   "note = float(input())\n__ note >= 10:\n    print('Admis')\n__:\n    print('Échec')",
      trous_js:   "let note = parseFloat(prompt());\nif (__) {\n    console.log('Admis');\n} __ {\n    console.log('Échec');\n}",
      scenario_algo: { titre: 'Classifier une note', enonce: "Écrire un algorithme qui lit une note et affiche : 'Très bien' (≥16), 'Bien' (≥13), 'Passable' (≥10), 'Insuffisant' (<10).", code: "Variable note : Réel\nDébut\n   Lire(note)\n   Si note >= 16 Alors\n      Écrire(\"Très bien\")\n   Sinon Si note >= 13 Alors\n      Écrire(\"Bien\")\n   Sinon Si note >= 10 Alors\n      Écrire(\"Passable\")\n   Sinon\n      Écrire(\"Insuffisant\")\n   FinSi\nFin" },
      scenario_py:  { titre: 'Classifier une note', enonce: "Écrire une fonction Python qui classe une note sur 20.", code: "def classifier_note(note):\n    if note >= 16:\n        return 'Très bien'\n    elif note >= 13:\n        return 'Bien'\n    elif note >= 10:\n        return 'Passable'\n    else:\n        return 'Insuffisant'\nnote = float(input('Note : '))\nprint(classifier_note(note))" },
      scenario_js:  { titre: 'Calculatrice simple', enonce: "Écrire une fonction JavaScript qui effectue +, -, ×, ÷ selon le signe saisi.", code: "function calculer(a, op, b) {\n  if (op === '+') return a + b;\n  else if (op === '-') return a - b;\n  else if (op === '*') return a * b;\n  else if (op === '/') return b !== 0 ? a / b : 'Division par zéro';\n}" },
    },
    syntaxe_fonction: {
      nom: 'Fonctions et Procédures',
      trous_algo: "Fonction Carre(n : __) : Entier\nDébut\n   Retourner __ * __\nFin\n\nVariable res : Entier\nDébut\n   res ← __(5)\n   Écrire(res)\nFin",
      trous_py:   "def carre(n):\n    return __ * __\n\nfor i in range(1, 6):\n    print(i, '² =', __(i))",
      trous_js:   "function carre(n) {\n    return __ * __;\n}\nconsole.log(__(5));",
      scenario_algo: { titre: 'Fonction carré', enonce: "Écrire une fonction Carré(n) qui retourne le carré d'un entier.", code: "Fonction Carré(n : Entier) : Entier\nDébut\n   Retourner n * n\nFin\n\nVariable i, res : Entier\nDébut\n   Pour i de 1 à 5 Faire\n      res ← Carré(i)\n      Écrire(i, \"² = \", res)\n   FinPour\nFin" },
      scenario_py:  { titre: 'Fonction factorielle', enonce: "Écrire une fonction Python factorielle(n) qui calcule n!.", code: "def factorielle(n):\n    if n <= 1:\n        return 1\n    return n * factorielle(n - 1)\n\nfor i in range(1, 8):\n    print(f'{i}! = {factorielle(i)}')" },
      scenario_js:  { titre: 'Fonction maximum', enonce: "Écrire une fonction JavaScript qui retourne le maximum de deux nombres.", code: "function maximum(a, b) {\n  return a >= b ? a : b;\n}\nconsole.log(maximum(12, 7));" },
    },
    syntaxe_tableau: {
      nom: 'Tableaux et Listes',
      trous_algo: "Variable T : Tableau[0..__] de Entier\nVariable i, max : Entier\nDébut\n   Pour i de __ à 9 Faire\n      Lire(T[__])\n   FinPour\n   max ← T[0]\n   Pour i de 1 à 9 Faire\n      Si T[i] > __ Alors\n         max ← __\n      FinSi\n   FinPour\nFin",
      trous_py:   "valeurs = []\nfor i in range(N):\n    valeurs.__(float(input()))\nmaxi = valeurs[__]\nfor v in valeurs:\n    if v > maxi:\n        maxi = __\nprint(maxi)",
      trous_js:   "let tab = [];\nfor (let i = 0; i < N; i++) {\n    tab.__(parseFloat(prompt()));\n}\nlet max = tab[__];\nfor (let v of tab) {\n    if (v > max) max = __;\n}\nconsole.log(max);",
      scenario_algo: { titre: 'Saisie et maximum', enonce: "Écrire un algorithme qui saisit 10 entiers dans un tableau et affiche le plus grand.", code: "Variable T : Tableau[0..9] de Entier\nVariable i, max : Entier\nDébut\n   Pour i de 0 à 9 Faire\n      Lire(T[i])\n   FinPour\n   max ← T[0]\n   Pour i de 1 à 9 Faire\n      Si T[i] > max Alors\n         max ← T[i]\n      FinSi\n   FinPour\n   Écrire(\"Maximum = \", max)\nFin" },
      scenario_py:  { titre: 'Saisie et maximum', enonce: "Écrire un programme Python qui saisit N valeurs dans une liste et affiche le maximum.", code: "N = int(input('Taille : '))\nvaleurs = []\nfor i in range(N):\n    valeurs.append(float(input(f'valeurs[{i}] = ')))\nprint('Maximum :', max(valeurs))" },
      scenario_js:  { titre: "Moyenne d'un tableau", enonce: "Écrire une fonction JavaScript qui calcule la moyenne d'un tableau de nombres.", code: "function moyenne(tab) {\n  const somme = tab.reduce((acc, v) => acc + v, 0);\n  return somme / tab.length;\n}\nconst notes = [12, 15, 9, 17, 11];\nconsole.log('Moyenne :', moyenne(notes));" },
    },
  };

  const meta = META[patType];
  if (!meta) return null;

  const sc = isAlgo ? meta.scenario_algo : (isPy ? meta.scenario_py : meta.scenario_js);
  const trou = isAlgo ? meta.trous_algo : (isPy ? meta.trous_py : meta.trous_js);

  if (level === 'facile') return {
    level: 'facile',
    title: `Syntaxe — ${meta.nom} : ${sc.titre}`,
    body: `<strong>Objectif :</strong> Comprendre et utiliser la ${meta.nom}.<br><br><strong>Énoncé :</strong> ${sc.enonce}<br><br><em>Conseil : identifiez d'abord la structure à utiliser, puis déclarez vos variables.</em>`,
    code: null,
  };
  if (level === 'moyen') return {
    level: 'moyen',
    title: `Bloom 2-3 — Comprendre et Appliquer — ${meta.nom}`,
    body: `<strong>Bloom 2 — Comprendre :</strong><br>Avant de compléter le code, expliquez en une phrase ce que fait cette structure et pourquoi chaque mot-clé est nécessaire.<br><br><strong>Bloom 3 — Appliquer :</strong><br>Complétez le code en remplaçant chaque <code>__</code> par le bon mot-clé ou la bonne valeur :`,
    code: trou,
  };
  return {
    level: 'difficile',
    title: `Bloom 4-5-6 — Analyser, Évaluer, Créer — ${meta.nom}`,
    body: `<strong>Bloom 4 — Analyser :</strong><br>Dans quel cas précis utiliser ${meta.nom} plutôt qu'une autre structure ? Quelles sont ses limites ?<br><br><strong>Bloom 5 — Évaluer :</strong><br>Pour l'énoncé suivant, justifiez votre choix de structure : <em>${sc.enonce}</em><br><br><strong>Bloom 6 — Créer :</strong><br>Écrivez un programme complet de zéro qui résout l'énoncé ci-dessus.`,
    code: sc.code,
  };
}

// ══════════════════════════════════════════════════════════════
//  GÉNÉRATEUR D'EXERCICES ANALYSE (Patterns 32-40)
// ══════════════════════════════════════════════════════════════

function makeAnalyseExercise(sec, level, patType, isAlgo, isPy) {
  const t = sec.title.trim();

  const ANALYSE_META = {
    comparaison: {
      nom: 'Comparaison',
      facile: `<strong>Objectif :</strong> Comparer deux concepts de «&nbsp;${t}&nbsp;».<br><br>1. Citez <strong>deux différences</strong> entre les éléments comparés.<br>2. Citez <strong>un point commun</strong>.<br>3. Dans quel cas choisiriez-vous l'un plutôt que l'autre ?`,
      moyen_body: `<strong>Bloom 3 — Appliquer :</strong><br>Remplissez le tableau comparatif :`,
      moyen_code: `Critère          | Élément A          | Élément B\n─────────────────┼────────────────────┼──────────────────\nCondition usage  | __________         | __________\nNb exécutions    | __________         | __________\nRisque principal | __________         | __________\nSyntaxe clé      | __________         | __________`,
      difficile: `<strong>Objectif :</strong> Rédiger une comparaison argumentée pour «&nbsp;${t}&nbsp;».<br><br>1. Présentez les deux éléments comparés.<br>2. Expliquez leurs différences avec des exemples concrets.<br>3. Concluez sur quand utiliser l'un vs l'autre.`,
    },
    erreur_piege: {
      nom: 'Erreur / Piège',
      facile: `<strong>Objectif :</strong> Identifier une erreur classique de la section «&nbsp;${t}&nbsp;».<br><br>1. Quelle est l'erreur décrite dans le cours ?<br>2. Pourquoi est-elle difficile à détecter ?<br>3. Comment l'éviter systématiquement ?`,
      moyen_body: `<strong>Bloom 3 — Appliquer :</strong><br>Ce code contient une erreur classique. Identifiez-la, expliquez-la et écrivez la version corrigée :`,
      moyen_code: isAlgo
        ? `Variable i, somme : Entier\nDébut\n   somme ← 0\n   Pour i de 1 à 10 Faire\n      i ← i + 2   // erreur ici\n      somme ← somme + i\n   FinPour\n   Écrire(somme)\nFin`
        : isPy
        ? `somme = 0\nfor i in range(1, 11):\n    i = i + 2  # erreur ici\n    somme += i\nprint(somme)`
        : `let somme = 0;\nfor (let i = 1; i <= 10; i++) {\n    i = i + 2; // erreur ici\n    somme += i;\n}\nconsole.log(somme);`,
      difficile: `<strong>Objectif :</strong> Analyser, corriger et prévenir une erreur.<br><br>1. Décrivez précisément l'erreur mentionnée.<br>2. Écrivez un exemple de code <strong>incorrect</strong>.<br>3. Écrivez la version <strong>corrigée</strong> avec explication.<br>4. Proposez une règle pour ne plus commettre cette erreur.`,
    },
    trace_execution: {
      nom: "Trace d'Exécution",
      facile: `<strong>Objectif :</strong> Comprendre le déroulement d'un algorithme de «&nbsp;${t}&nbsp;».<br><br>1. Combien d'itérations effectue la boucle si N = 4 ?<br>2. Quelle est la valeur finale de la variable de résultat ?<br>3. Que se passe-t-il si N = 0 ?`,
      moyen_body: `<strong>Bloom 3 — Appliquer :</strong><br>Complétez le tableau de trace :`,
      moyen_code: `i    | condition | instruction      | somme\n─────┼───────────┼──────────────────┼──────\ninit |    —      | somme ← 0        |   0\n  1  | 1 <= N ?  | somme ← 0 + 1    | ____\n  2  | 2 <= N ?  | somme ← __ + 2   | ____\n  3  | 3 <= N ?  | somme ← __ + 3   | ____\n  4  | 4 <= N ?  | somme ← __ + 4   | ____\n  5  | 5 <= N ?  | sortie boucle    | ____`,
      difficile: `<strong>Objectif :</strong> Tracer complètement l'exécution avec N = 5.<br><br>1. Construisez le tableau de trace complet.<br>2. Indiquez la valeur de chaque variable après chaque étape.<br>3. Donnez le résultat final et vérifiez-le manuellement.`,
    },
    entree_sortie: {
      nom: 'Entrées / Sorties',
      facile: `<strong>Objectif :</strong> Identifier le contrat d'interface de «&nbsp;${t}&nbsp;».<br><br>1. Listez toutes les données en entrée (nom, type, contrainte).<br>2. Décrivez la valeur retournée en sortie.<br>3. Que retourne la fonction si les données sont invalides ?`,
      moyen_body: `<strong>Bloom 3 — Appliquer :</strong><br>Remplissez le schéma entrée/sortie de la fonction :`,
      moyen_code: `FONCTION __________(________ : ________, ________ : ________) : ________\n┌─────────────────────────────────────────┐\n│  Entrées  : __________ : __________     │\n│  Sortie   : __________ : __________     │\n│  Précond  : __________                  │\n└─────────────────────────────────────────┘`,
      difficile: `<strong>Objectif :</strong> Concevoir et documenter une fonction complète.<br><br>1. Définissez les entrées avec leur type et contraintes.<br>2. Définissez la sortie avec son type.<br>3. Écrivez la signature complète.<br>4. Implémentez le corps de la fonction.`,
    },
    preconditions: {
      nom: 'Préconditions / Postconditions',
      facile: `<strong>Objectif :</strong> Comprendre le contrat de l'algorithme «&nbsp;${t}&nbsp;».<br><br>1. Quelle est la précondition principale ?<br>2. Quelle est la postcondition ?<br>3. Que se passe-t-il si la précondition n'est pas respectée ?`,
      moyen_body: `<strong>Bloom 3 — Appliquer :</strong><br>Complétez le contrat formel :`,
      moyen_code: `ALGORITHME : __________\n─────────────────────────────────────────\nPRÉCONDITION  : __________\n─────────────────────────────────────────\nPOSTCONDITION : __________`,
      difficile: `<strong>Objectif :</strong> Rédiger le contrat complet.<br><br>1. Rédigez toutes les préconditions avec justification.<br>2. Rédigez toutes les postconditions.<br>3. Écrivez le code qui vérifie les préconditions.<br>4. Donnez un appel valide et un appel invalide.`,
    },
    conversion_langage: {
      nom: 'Conversion entre Langages',
      facile: `<strong>Objectif :</strong> Reconnaître les équivalences de «&nbsp;${t}&nbsp;».<br><br>1. Identifiez la structure algorithmique principale.<br>2. Donnez sa syntaxe en algorithmique.<br>3. Donnez son équivalent en Python.<br>4. Donnez son équivalent en JavaScript.`,
      moyen_body: `<strong>Bloom 3 — Appliquer :</strong><br>Complétez la table de correspondance :`,
      moyen_code: `Algorithmique             | Python                | JavaScript\n──────────────────────────┼───────────────────────┼──────────────────────\nPOUR i DE 1 À N FAIRE     | __________            | __________\nTANT QUE cond FAIRE       | __________            | __________\nSI cond ALORS...SINON     | __________            | __________\nFONCTION f(n:Entier):Réel | __________            | __________\nRETOURNER valeur          | __________            | __________`,
      difficile: `<strong>Objectif :</strong> Traduire un algorithme complet.<br><br>1. Écrivez l'algorithme complet en notation algorithmique.<br>2. Traduisez-le en Python.<br>3. Traduisez-le en JavaScript.<br>4. Signalez les différences syntaxiques notables.`,
    },
    complexite: {
      nom: 'Complexité / Efficacité',
      facile: `<strong>Objectif :</strong> Analyser la complexité de «&nbsp;${t}&nbsp;».<br><br>1. Quelle est la complexité en temps ? (O(1), O(n), O(n²)…)<br>2. Justifiez en comptant le nombre d'opérations.<br>3. Existe-t-il un algorithme plus efficace ?`,
      moyen_body: `<strong>Bloom 3 — Appliquer :</strong><br>Comparez deux algorithmes :`,
      moyen_code: `Critère               | Algo A (boucle simple) | Algo B (boucles imbriquées)\n──────────────────────┼────────────────────────┼────────────────────────────\nNb boucles            | 1                      | 2 imbriquées\nNb opérations (N=10)  | __________             | __________\nNb opérations (N=100) | __________             | __________\nComplexité            | __________             | __________`,
      difficile: `<strong>Objectif :</strong> Analyser et optimiser un algorithme.<br><br>1. Déterminez la complexité en temps et en espace.<br>2. Calculez le nombre d'opérations pour N=10, N=100, N=1000.<br>3. Identifiez le goulot d'étranglement.<br>4. Proposez une version optimisée.`,
    },
    regle_absolue: {
      nom: 'Règle Absolue',
      facile: `<strong>Objectif :</strong> Retenir les règles fondamentales de «&nbsp;${t}&nbsp;».<br><br>1. Énoncez la règle principale décrite dans le cours.<br>2. Donnez un exemple de code qui <strong>respecte</strong> cette règle.<br>3. Donnez un exemple qui l'<strong>enfreint</strong> et expliquez les conséquences.`,
      moyen_body: `<strong>Bloom 3 — Appliquer :</strong><br>Complétez l'énoncé de chaque règle :`,
      moyen_code: `Règle 1 : Il faut toujours __________ une variable avant de __________.\nRègle 2 : On ne doit jamais __________ la variable de contrôle dans une boucle.\nRègle 3 : Toute fonction récursive doit avoir un __________.\nRègle 4 : Un diviseur ne doit jamais valoir __________ avant une division.\nRègle 5 : L'indice d'un tableau doit être entre __ et __ pour N éléments.`,
      difficile: `<strong>Objectif :</strong> Justifier et illustrer une règle absolue.<br><br>1. Énoncez la règle de manière précise et complète.<br>2. Expliquez pourquoi cette règle est fondamentale.<br>3. Donnez un exemple qui la respecte.<br>4. Donnez un exemple qui la viole et montrez le bug produit.`,
    },
    schema: {
      nom: 'Schéma / Organigramme',
      facile: `<strong>Objectif :</strong> Comprendre une représentation graphique de «&nbsp;${t}&nbsp;».<br><br>1. Décrivez en mots ce que représente le schéma.<br>2. Identifiez les symboles utilisés et leur signification.<br>3. Reliez le schéma à l'algorithme correspondant.`,
      moyen_body: `<strong>Bloom 3 — Appliquer :</strong><br>Remplissez les éléments manquants de l'organigramme :`,
      moyen_code: `  ┌─────────────────────┐\n  │  __________         │  ← Initialisation\n  └──────────┬──────────┘\n             ↓\n   [__________?] ──Non──→  __________ (fin)\n             │ Oui\n             ↓\n   ┌─────────────────┐\n   │  __________     │  ← Corps de la boucle\n   └────────┬────────┘\n            └────────────↑  (retour condition)`,
      difficile: `<strong>Objectif :</strong> Construire un organigramme complet pour «&nbsp;${t}&nbsp;».<br><br>1. Dessinez l'organigramme complet.<br>2. Utilisez les symboles standard : ovale, rectangle, losange.<br>3. Annotez chaque bloc et indiquez les flèches.`,
    },
  };

  const meta = ANALYSE_META[patType];
  if (!meta) return null;

  if (level === 'facile') return { level: 'facile', title: `${meta.nom} — ${t}`, body: meta.facile, code: null };
  if (level === 'moyen') return {
    level: 'moyen',
    title: `Bloom 2-3 — Comprendre et Appliquer — ${meta.nom} — ${t}`,
    body: `<strong>Bloom 2 — Comprendre :</strong><br>Expliquez avec vos propres mots le principe de cet exercice et pourquoi il est important dans le contexte de «&nbsp;${t}&nbsp;».<br><br>${meta.moyen_body}`,
    code: meta.moyen_code,
  };
  return { level: 'difficile', title: `Bloom 4-5-6 — Analyser, Évaluer, Créer — ${meta.nom} — ${t}`, body: meta.difficile, code: null };
}

// ══════════════════════════════════════════════════════════════
//  GÉNÉRATEUR D'EXERCICES TEXTUEL (Patterns 1-24)
// ══════════════════════════════════════════════════════════════

const TYPE_LABELS = {
  definition: 'les notions', cause: 'les causes', consequence: 'les conséquences',
  etape: 'les étapes / processus', caracteristique: 'les caractéristiques',
  fonction: 'les fonctions / rôles', exemple: 'les exemples', date: 'les dates et événements',
  avantage: 'les avantages et inconvénients', classification: 'les classifications',
  condition: 'les conditions / critères', acteur: 'les acteurs / auteurs',
  formule: 'les formules / lois', chiffre: 'les chiffres / données',
  localisation: 'les localisations', composition: 'la composition / structure',
  synonyme: 'les synonymes', exception: 'les exceptions',
  abreviation: 'les abréviations et acronymes', tableau: 'les formats',
  remarque: 'les notes importantes', traduction: 'les traductions algo-code',
  objectif: 'les objectifs / buts', structure: 'la syntaxe / structure',
};

function makeBloomMoyenBody(patType, kw1, kw2) {
  const BLOOM_MOYEN = {
    definition: `<strong>Bloom 2 — Comprendre :</strong><br>Reformulez avec vos propres mots la définition de <em>${kw1}</em>. Résumez en 2 phrases. Expliquez la différence entre <em>${kw1}</em> et <em>${kw2}</em>.<br><br><strong>Bloom 3 — Appliquer :</strong><br>Utilisez la notion de <em>${kw1}</em> pour expliquer une situation concrète de votre vie quotidienne.`,
    cause: `<strong>Bloom 2 — Comprendre :</strong><br>Résumez avec vos propres mots les causes de <em>${kw1}</em>. Expliquez le mécanisme.<br><br><strong>Bloom 3 — Appliquer :</strong><br>Identifiez dans une situation réelle les mêmes types de causes que celles étudiées pour <em>${kw1}</em>.`,
    consequence: `<strong>Bloom 2 — Comprendre :</strong><br>Expliquez les conséquences de <em>${kw1}</em>. Résumez les 3 effets principaux.<br><br><strong>Bloom 3 — Appliquer :</strong><br>Prédisez les conséquences d'un cas similaire de votre choix.`,
    etape: `<strong>Bloom 2 — Comprendre :</strong><br>Expliquez chaque étape de <em>${kw1}</em>. Justifiez l'ordre logique.<br><br><strong>Bloom 3 — Appliquer :</strong><br>Appliquez ce processus à une situation concrète de votre choix.`,
    caracteristique: `<strong>Bloom 2 — Comprendre :</strong><br>Expliquez pourquoi chaque caractéristique de <em>${kw1}</em> est importante. Reformulez sans regarder vos notes.<br><br><strong>Bloom 3 — Appliquer :</strong><br>Utilisez les caractéristiques de <em>${kw1}</em> comme grille d'analyse d'un exemple concret.`,
    fonction: `<strong>Bloom 2 — Comprendre :</strong><br>Expliquez le rôle et la fonction de <em>${kw1}</em>. Que se passerait-il s'il n'existait pas ?<br><br><strong>Bloom 3 — Appliquer :</strong><br>Montrez comment <em>${kw1}</em> s'applique dans une situation pratique concrète.`,
    exemple: `<strong>Bloom 2 — Comprendre :</strong><br>Expliquez pourquoi les exemples de <em>${kw1}</em> sont représentatifs. Quel point commun partagent-ils ?<br><br><strong>Bloom 3 — Appliquer :</strong><br>Trouvez un exemple de <em>${kw1}</em> dans votre environnement quotidien.`,
    avantage: `<strong>Bloom 2 — Comprendre :</strong><br>Expliquez pourquoi <em>${kw1}</em> présente des avantages et des inconvénients. Résumez les 2 principaux de chaque.<br><br><strong>Bloom 3 — Appliquer :</strong><br>Montrez comment vous utiliseriez <em>${kw1}</em> en tenant compte de ses limites.`,
  };
  return BLOOM_MOYEN[patType] || `<strong>Bloom 2 — Comprendre :</strong><br>Reformulez avec vos propres mots les concepts de <em>${kw1}</em>.<br><br><strong>Bloom 3 — Appliquer :</strong><br>Utilisez ce que vous avez appris pour traiter un exemple concret de votre choix.`;
}

function makeBloomDifficileBody(patType, kw1, secTitle) {
  const bodies = {
    definition: `<strong>Bloom 4 — Analyser :</strong><br>Analysez la définition de <em>${kw1}</em> : identifiez ses conditions d'applicabilité, ses limites et ses variantes.<br><br><strong>Bloom 5 — Évaluer :</strong><br>Évaluez deux définitions alternatives de <em>${kw1}</em> trouvées dans la littérature. Laquelle est la plus rigoureuse et pourquoi ?<br><br><strong>Bloom 6 — Créer :</strong><br>Rédigez une définition originale de <em>${kw1}</em> qui intègre tous ses aspects essentiels. Accompagnez-la d'un exemple et d'un contre-exemple.`,
    cause: `<strong>Bloom 4 — Analyser :</strong><br>Analysez les relations entre les différentes causes de <em>${kw1}</em> : lesquelles sont primaires, secondaires, déclenchantes ?<br><br><strong>Bloom 5 — Évaluer :</strong><br>Évaluez l'importance relative de chaque cause. Laquelle serait la plus facile à éliminer ?<br><br><strong>Bloom 6 — Créer :</strong><br>Construisez un schéma causal complet montrant les liens entre toutes les causes et les effets de <em>${kw1}</em>.`,
    consequence: `<strong>Bloom 4 — Analyser :</strong><br>Analysez les conséquences à court terme vs à long terme de <em>${kw1}</em>. Distinguez effets directs et indirects.<br><br><strong>Bloom 5 — Évaluer :</strong><br>Quelle est la conséquence la plus grave ? Justifiez votre classement.<br><br><strong>Bloom 6 — Créer :</strong><br>Proposez un plan d'action pour atténuer les conséquences négatives de <em>${kw1}</em>.`,
  };
  return bodies[patType] || `<strong>Bloom 4 — Analyser :</strong><br>Analysez en profondeur les concepts de la section «&nbsp;${secTitle}&nbsp;» : identifiez les relations, les limites et les cas particuliers.<br><br><strong>Bloom 5 — Évaluer :</strong><br>Évaluez la pertinence de ces concepts dans un contexte réel. Quelles sont les situations où ils ne s'appliquent pas ?<br><br><strong>Bloom 6 — Créer :</strong><br>Créez un exercice original à destination d'autres étudiants sur le thème de «&nbsp;${secTitle}&nbsp;». Incluez l'énoncé, les réponses attendues et les critères d'évaluation.`;
}

function makeTextualExercise(sec, level, patType, patData) {
  const t = sec.title.trim();

  if (level === 'facile') {
    if (patType && patData.length) {
      const itemsHtml = patData.slice(0, 6).map((d, i) => `${i + 1}. ${d.question}`).join('<br>');
      return {
        level: 'facile',
        title: `Questions de cours — ${t}`,
        body: `<strong>Objectif :</strong> Vérifier la compréhension de ${TYPE_LABELS[patType] || 'ce chapitre'}.<br><br>Répondez aux questions suivantes :<br><br>${itemsHtml}`,
        code: null,
      };
    }
    return {
      level: 'facile',
      title: `Questions de cours — ${t}`,
      body: `<strong>Objectif :</strong> Vérifier la compréhension de ce chapitre.<br><br>Répondez aux questions suivantes :<br><br>1. Expliquez en vos propres mots : ${t}.<br>2. Donnez un exemple concret illustrant ${t}.<br>3. Quelle est l'utilité principale de ${t} ?`,
      code: null,
    };
  }

  if (level === 'moyen') {
    if (patType && patData.length) {
      const kw1 = patData[0].keyword;
      const kw2 = patData.length > 1 ? patData[1].keyword : kw1;
      return {
        level: 'moyen',
        title: `Bloom 2-3 — Comprendre et Appliquer — ${t}`,
        body: makeBloomMoyenBody(patType, kw1, kw2),
        code: null,
      };
    }
    return {
      level: 'moyen',
      title: `Bloom 2-3 — Comprendre et Appliquer — ${t}`,
      body: `<strong>Bloom 2 — Comprendre :</strong><br>Reformulez avec vos propres mots les concepts principaux de «&nbsp;${t}&nbsp;».<br><br><strong>Bloom 3 — Appliquer :</strong><br>Utilisez ces concepts pour résoudre un exemple concret de votre choix.`,
      code: null,
    };
  }

  // Difficile
  const kw1 = patType && patData.length ? patData[0].keyword : t;
  return {
    level: 'difficile',
    title: `Bloom 4-5-6 — Analyser, Évaluer, Créer — ${t}`,
    body: makeBloomDifficileBody(patType, kw1, t),
    code: null,
  };
}

// ══════════════════════════════════════════════════════════════
//  POINT D'ENTRÉE PRINCIPAL
// ══════════════════════════════════════════════════════════════

export async function analyzeCourse(courseText) {
  const [lang, langLabel] = detectLang(courseText);
  const sections = detectSections(courseText);
  const courseName = detectCourseName(courseText);
  return { lang, langLabel, sections, courseName };
}

export async function generateExercises({ exName, sections, difficulty, lang }) {
  const diffs = difficulty === 'progressif' ? ['facile', 'moyen', 'difficile'] : [difficulty];
  const isAlgo = lang === 'algo';
  const isPy   = lang === 'python';
  const out = [];

  for (const sec of sections) {
    const [patType, patData] = detectBestPattern(sec);
    const _ANALYSE_PATTERNS = new Set(['comparaison', 'erreur_piege', 'trace_execution', 'entree_sortie', 'preconditions', 'conversion_langage', 'complexite', 'regle_absolue', 'schema']);

    for (const d of diffs) {
      let ex = null;

      if (patType && patType.startsWith('syntaxe_')) {
        ex = makeSyntaxeExercise(sec, d, patType, isAlgo, isPy);
      } else if (patType && _ANALYSE_PATTERNS.has(patType)) {
        ex = makeAnalyseExercise(sec, d, patType, isAlgo, isPy);
      }

      if (!ex) {
        ex = makeTextualExercise(sec, d, patType, patData);
      }

      ex.title = `Exercice ${out.length + 1} — ${sec.title}`;
      ex.section = sec;
      out.push(ex);
    }
  }

  return out;
}
