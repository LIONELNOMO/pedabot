import supabase from '../../../lib/supabase.js';
import { cors, requireAuth } from '../../../lib/auth.js';

export default async function handler(req, res) {
  cors(res);
  if (req.method === 'OPTIONS') return res.status(200).end();

  const { token, action } = req.query;
  if (!token) return res.status(400).json({ detail: 'Token requis' });

  // ─── POST /api/eleve/:token/submit (anonyme) ───
  if (action === 'submit' && req.method === 'POST') {
    const { eleve_prenom, reponses } = req.body || {};
    if (!eleve_prenom || !reponses) return res.status(400).json({ detail: 'Prénom et réponses requis' });

    const { data: link } = await supabase
      .from('sharedlink')
      .select('token')
      .eq('token', token)
      .maybeSingle();

    if (!link) return res.status(404).json({ detail: 'Lien invalide' });

    const { error } = await supabase
      .from('submission')
      .insert({
        token,
        eleve_prenom: String(eleve_prenom).trim(),
        reponses: String(reponses).trim(),
      });

    if (error) return res.status(500).json({ detail: 'Erreur soumission' });

    return res.status(201).json({ message: 'Réponse enregistrée' });
  }

  // ─── GET /api/eleve/:token/submissions (prof) ───
  if (action === 'submissions' && req.method === 'GET') {
    const user = requireAuth(req);
    if (!user || user.role !== 'prof') return res.status(403).json({ detail: 'Accès réservé aux professeurs' });

    const { data: link } = await supabase
      .from('sharedlink')
      .select('token, teacher_id')
      .eq('token', token)
      .maybeSingle();

    if (!link) return res.status(404).json({ detail: 'Lien introuvable' });
    if (link.teacher_id !== Number(user.sub)) return res.status(403).json({ detail: 'Accès interdit' });

    const { data: subs, error } = await supabase
      .from('submission')
      .select('id, eleve_prenom, reponses, submitted_at')
      .eq('token', token)
      .order('submitted_at', { ascending: false });

    if (error) return res.status(500).json({ detail: 'Erreur récupération soumissions' });

    return res.status(200).json(subs ?? []);
  }

  return res.status(404).json({ detail: 'Action inconnue' });
}
