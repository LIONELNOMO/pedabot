import supabase from '../../../lib/supabase.js';
import { cors, requireAuth } from '../../../lib/auth.js';

export default async function handler(req, res) {
  cors(res);
  if (req.method === 'OPTIONS') return res.status(200).end();
  if (req.method !== 'POST') return res.status(405).json({ detail: 'Method not allowed' });

  const user = requireAuth(req);
  if (!user) return res.status(401).json({ detail: 'Non authentifié' });

  const { id, action } = req.query;

  // ─── POST /api/exercice/:id/submit (élève) ───
  if (action === 'submit') {
    if (user.role !== 'eleve') return res.status(403).json({ detail: 'Réservé aux élèves' });

    const { reponses } = req.body || {};
    if (!id || !reponses) return res.status(400).json({ detail: 'ID et réponses requis' });

    const { data: a } = await supabase
      .from('assignment')
      .select('id, submitted_at')
      .eq('id', Number(id))
      .eq('eleve_email', String(user.email).toLowerCase().trim())
      .maybeSingle();

    if (!a) return res.status(404).json({ detail: 'Exercice introuvable' });
    if (a.submitted_at) return res.status(409).json({ detail: 'Déjà soumis' });

    const { error } = await supabase
      .from('assignment')
      .update({ reponses: String(reponses).trim(), submitted_at: new Date().toISOString() })
      .eq('id', Number(id));

    if (error) {
      console.error('submit assignment update error:', error);
      return res.status(500).json({ detail: 'Erreur soumission' });
    }

    return res.status(201).json({ message: 'Réponse enregistrée' });
  }

  // ─── POST /api/exercice/:id/feedback (prof) ───
  if (action === 'feedback') {
    if (user.role !== 'prof') return res.status(403).json({ detail: 'Réservé aux professeurs' });

    const { feedback } = req.body || {};
    if (!id || !feedback) return res.status(400).json({ detail: 'ID et feedback requis' });

    const { data: a } = await supabase
      .from('assignment')
      .select('id, teacher_id')
      .eq('id', Number(id))
      .maybeSingle();

    if (!a) return res.status(404).json({ detail: 'Devoir introuvable' });
    if (Number(a.teacher_id) !== Number(user.sub))
      return res.status(403).json({ detail: 'Vous n\'êtes pas le créateur de ce devoir' });

    const { error } = await supabase
      .from('assignment')
      .update({
        feedback: String(feedback).trim(),
        feedback_at: new Date().toISOString(),
        corrige_visible: true,
      })
      .eq('id', Number(id));

    if (error) {
      console.error('feedback update error:', error);
      return res.status(500).json({ detail: 'Erreur envoi feedback' });
    }

    return res.status(201).json({ message: 'Feedback envoyé' });
  }

  return res.status(404).json({ detail: 'Action inconnue' });
}
