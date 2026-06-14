import supabase from '../../../lib/supabase.js';
import { cors, requireAuth } from '../../../lib/auth.js';

export default async function handler(req, res) {
  cors(res);
  if (req.method === 'OPTIONS') return res.status(200).end();

  const { token, action } = req.query;
  if (!token) return res.status(400).json({ error: 'Token requis' });

  if (action === 'submit' && req.method === 'POST') {
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

  if (action === 'submissions' && req.method === 'GET') {
    const user = requireAuth(req);
    if (!user || user.role !== 'prof') return res.status(403).json({ error: 'Accès réservé aux professeurs' });

    const { data: link, error: linkErr } = await supabase
      .from('sharedlink')
      .select('exercise_id')
      .eq('token', token)
      .eq('prof_id', user.sub)
      .single();

    if (linkErr || !link) return res.status(404).json({ error: 'Lien introuvable' });

    const { data: subs, error } = await supabase
      .from('submission')
      .select('id, nom_eleve, reponse, created_at')
      .eq('exercise_id', link.exercise_id)
      .order('created_at', { ascending: false });

    if (error) return res.status(500).json({ error: 'Erreur récupération soumissions' });

    return res.status(200).json(subs);
  }

  return res.status(404).json({ error: 'Action inconnue' });
}
