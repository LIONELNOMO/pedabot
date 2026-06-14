import { v4 as uuidv4 } from 'uuid';
import supabase from '../../lib/supabase.js';
import { cors, requireAuth } from '../../lib/auth.js';

export default async function handler(req, res) {
  cors(res);
  if (req.method === 'OPTIONS') return res.status(200).end();

  const user = requireAuth(req);
  if (!user || user.role !== 'prof') return res.status(403).json({ error: 'Accès réservé aux professeurs' });

  const { action } = req.query;

  if (action === 'mine' && req.method === 'GET') {
    const { data: exercises, error } = await supabase
      .from('exercisedb')
      .select(`
        id, nom, contenu, created_at,
        sharedlink (token),
        submission (count)
      `)
      .eq('prof_id', user.sub)
      .order('created_at', { ascending: false });

    if (error) return res.status(500).json({ error: 'Erreur récupération exercices' });

    const result = exercises.map(ex => ({
      id: ex.id,
      nom: ex.nom,
      contenu: ex.contenu,
      created_at: ex.created_at,
      token: ex.sharedlink?.[0]?.token ?? null,
      nb_soumissions: ex.submission?.[0]?.count ?? 0,
    }));

    return res.status(200).json(result);
  }

  if (action === 'share' && req.method === 'POST') {
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

  if (action === 'assign' && req.method === 'POST') {
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

  return res.status(404).json({ error: 'Action inconnue' });
}
