import supabase from '../../lib/supabase.js';
import { hashPassword, verifyPassword, createToken, cors } from '../../lib/auth.js';

export default async function handler(req, res) {
  cors(res);
  if (req.method === 'OPTIONS') return res.status(200).end();
  if (req.method !== 'POST') return res.status(405).json({ detail: 'Method not allowed' });

  const { action } = req.query;

  if (action === 'login') {
    const { email, password } = req.body || {};
    if (!email || !password) return res.status(400).json({ detail: 'Email et mot de passe requis' });

    const { data: user } = await supabase
      .from('user')
      .select('id, email, nom, role, password_hash')
      .eq('email', String(email).toLowerCase().trim())
      .maybeSingle();

    if (!user) return res.status(401).json({ detail: 'Identifiants invalides' });
    if (!verifyPassword(password, user.password_hash))
      return res.status(401).json({ detail: 'Identifiants invalides' });

    const token = createToken(user.id, user.email, user.nom, user.role);
    return res.status(200).json({
      token,
      user: { id: user.id, email: user.email, nom: user.nom, role: user.role },
    });
  }

  if (action === 'register') {
    const { email, password, nom, role } = req.body || {};
    if (!email || !password || !nom) return res.status(400).json({ detail: 'Champs requis manquants' });

    const userRole = ['prof', 'eleve'].includes(role) ? role : 'prof';
    const cleanEmail = String(email).toLowerCase().trim();

    const { data: existing } = await supabase
      .from('user')
      .select('id')
      .eq('email', cleanEmail)
      .maybeSingle();

    if (existing) return res.status(409).json({ detail: 'Email déjà utilisé' });

    const password_hash = hashPassword(password);

    const { data: user, error } = await supabase
      .from('user')
      .insert({ email: cleanEmail, password_hash, nom, role: userRole })
      .select('id, email, nom, role')
      .single();

    if (error) return res.status(500).json({ detail: 'Erreur lors de la création du compte' });

    const token = createToken(user.id, user.email, user.nom, user.role);
    return res.status(201).json({
      token,
      user: { id: user.id, email: user.email, nom: user.nom, role: user.role },
    });
  }

  return res.status(404).json({ detail: 'Action inconnue' });
}
