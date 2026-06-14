import { generateExercises } from '../lib/engine.js';
import { cors, requireAuth } from '../lib/auth.js';

export default async function handler(req, res) {
  cors(res);
  if (req.method === 'OPTIONS') return res.status(200).end();
  if (req.method !== 'POST') return res.status(405).json({ error: 'Method not allowed' });

  const user = requireAuth(req);
  if (!user) return res.status(401).json({ error: 'Non authentifié' });

  const { exName, sections, difficulty, lang } = req.body || {};
  if (!exName || !sections || !difficulty)
    return res.status(400).json({ error: 'Champs requis manquants' });

  try {
    const exercises = generateExercises({ exName, sections, difficulty, lang });
    return res.status(200).json(exercises);
  } catch (e) {
    return res.status(500).json({ error: 'Erreur génération exercices' });
  }
}
