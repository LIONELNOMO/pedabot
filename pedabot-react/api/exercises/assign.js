import supabase from '../../lib/supabase.js';
import { cors, requireAuth } from '../../lib/auth.js';

export default async function handler(req, res) {
  cors(res);
  if (req.method === 'OPTIONS') return res.status(200).end();
  if (req.method !== 'POST') return res.status(405).json({ error: 'Method not allowed' });

  const user = requireAuth(req);
  if (!user || user.role !== 'prof') return res.status(403).json({ error: 'Accès réservé aux professeurs' });

  const { exercise_id, eleve_ids } = req.body || {};
  if (!exercise_id || !Array.isArray(eleve_ids) || eleve_ids.length === 0)
    return res.status(400).json({ error: 'exercise_id et eleve_ids requis' });

  const { data: ex, error: exErr } = await supabase
    .from('exercisedb')
    .select('id')
    .eq('id', exercise_id)
    .eq('prof_id', user.sub)
    .single();

  if (exErr || !ex) return res.status(404).json({ error: 'Exercice introuvable' });

  const rows = eleve_ids.map(eleve_id => ({ exercise_id, eleve_id, statut: 'assigné' }));

  const { error } = await supabase.from('assignment').upsert(rows, {
    onConflict: 'exercise_id,eleve_id',
    ignoreDuplicates: true,
  });

  if (error) return res.status(500).json({ error: 'Erreur assignation' });

  return res.status(201).json({ message: `Exercice assigné à ${eleve_ids.length} élève(s)` });
}
