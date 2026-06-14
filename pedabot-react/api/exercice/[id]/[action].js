import supabase from '../../../lib/supabase.js';
import { cors, requireAuth } from '../../../lib/auth.js';

export default async function handler(req, res) {
  cors(res);
  if (req.method === 'OPTIONS') return res.status(200).end();
  if (req.method !== 'POST') return res.status(405).json({ error: 'Method not allowed' });

  const user = requireAuth(req);
  if (!user || user.role !== 'eleve') return res.status(403).json({ error: 'Accès réservé aux élèves' });

  const { id, action } = req.query;
  if (action !== 'submit') return res.status(404).json({ error: 'Action inconnue' });

  const { reponse } = req.body || {};
  if (!id || !reponse) return res.status(400).json({ error: 'ID et réponse requis' });

  const { data: assignment, error: aErr } = await supabase
    .from('assignment')
    .select('id, exercise_id, statut')
    .eq('id', id)
    .eq('eleve_id', user.sub)
    .single();

  if (aErr || !assignment) return res.status(404).json({ error: 'Exercice introuvable' });
  if (assignment.statut === 'rendu') return res.status(409).json({ error: 'Déjà soumis' });

  const { error: subErr } = await supabase
    .from('submission')
    .insert({ exercise_id: assignment.exercise_id, eleve_id: user.sub, reponse, assignment_id: id });

  if (subErr) return res.status(500).json({ error: 'Erreur soumission' });

  await supabase.from('assignment').update({ statut: 'rendu' }).eq('id', id);

  return res.status(201).json({ message: 'Réponse enregistrée' });
}
