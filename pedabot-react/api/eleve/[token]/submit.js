import supabase from '../../../lib/supabase.js';
import { cors } from '../../../lib/auth.js';

export default async function handler(req, res) {
  cors(res);
  if (req.method === 'OPTIONS') return res.status(200).end();
  if (req.method !== 'POST') return res.status(405).json({ error: 'Method not allowed' });

  const { token } = req.query;
  if (!token) return res.status(400).json({ error: 'Token requis' });

  const { nom_eleve, reponse } = req.body || {};
  if (!nom_eleve || !reponse) return res.status(400).json({ error: 'Nom et réponse requis' });

  const { data: link, error: linkErr } = await supabase
    .from('sharedlink')
    .select('exercise_id')
    .eq('token', token)
    .single();

  if (linkErr || !link) return res.status(404).json({ error: 'Lien invalide' });

  const { error } = await supabase
    .from('submission')
    .insert({ exercise_id: link.exercise_id, nom_eleve, reponse });

  if (error) return res.status(500).json({ error: 'Erreur soumission' });

  return res.status(201).json({ message: 'Réponse enregistrée' });
}
