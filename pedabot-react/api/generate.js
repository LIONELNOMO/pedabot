import { generateExercises } from '../lib/engine.js';
import { cors } from '../lib/auth.js';

export default async function handler(req, res) {
  cors(res);
  if (req.method === 'OPTIONS') return res.status(200).end();
  if (req.method !== 'POST') return res.status(405).json({ detail: 'Method not allowed' });

  const { exName, sections, difficulty, lang, appro } = req.body || {};
  if (!exName || !Array.isArray(sections) || sections.length === 0 || !difficulty)
    return res.status(400).json({ detail: 'Champs requis manquants' });

  try {
    const exercises = await generateExercises({ exName, sections, difficulty, lang, appro });
    return res.status(200).json({ exercises });
  } catch (e) {
    return res.status(500).json({ detail: 'Erreur génération exercices' });
  }
}
