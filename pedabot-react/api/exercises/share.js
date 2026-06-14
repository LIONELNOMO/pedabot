import { v4 as uuidv4 } from 'uuid';
import supabase from '../../lib/supabase.js';
import { cors, requireAuth } from '../../lib/auth.js';

export default async function handler(req, res) {
  cors(res);
  if (req.method === 'OPTIONS') return res.status(200).end();
  if (req.method !== 'POST') return res.status(405).json({ error: 'Method not allowed' });

  const user = requireAuth(req);
  if (!user || user.role !== 'prof') return res.status(403).json({ error: 'Accès réservé aux professeurs' });

  const { nom, contenu } = req.body || {};
  if (!nom || !contenu) return res.status(400).json({ error: 'Nom et contenu requis' });

  const token = uuidv4();

  const { data: ex, error: exErr } = await supabase
    .from('exercisedb')
    .insert({ prof_id: user.sub, nom, contenu })
    .select('id')
    .single();

  if (exErr) return res.status(500).json({ error: 'Erreur sauvegarde exercice' });

  const { error: linkErr } = await supabase
    .from('sharedlink')
    .insert({ token, exercise_id: ex.id, prof_id: user.sub });

  if (linkErr) return res.status(500).json({ error: 'Erreur création lien' });

  return res.status(201).json({ token, exercise_id: ex.id });
}
