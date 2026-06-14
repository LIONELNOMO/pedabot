import { analyzeCourse } from '../lib/engine.js';
import { cors, requireAuth } from '../lib/auth.js';

export default async function handler(req, res) {
  cors(res);
  if (req.method === 'OPTIONS') return res.status(200).end();
  if (req.method !== 'POST') return res.status(405).json({ error: 'Method not allowed' });

  const user = requireAuth(req);
  if (!user) return res.status(401).json({ error: 'Non authentifié' });

  const { text } = req.body || {};
  if (!text || typeof text !== 'string' || !text.trim())
    return res.status(400).json({ error: 'Texte requis' });

  try {
    const result = analyzeCourse(text);
    return res.status(200).json(result);
  } catch (e) {
    return res.status(500).json({ error: 'Erreur analyse du cours' });
  }
}
