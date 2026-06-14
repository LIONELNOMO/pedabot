import supabase from '../../lib/supabase.js';
import { hashPassword, verifyPassword, createToken, cors } from '../../lib/auth.js';

export default async function handler(req, res) {
  cors(res);
  if (req.method === 'OPTIONS') return res.status(200).end();
  if (req.method !== 'POST') return res.status(405).json({ error: 'Method not allowed' });

  const { action } = req.query;

  if (action === 'login') {
    const { email, password } = req.body || {};
    if (!email || !password) return res.status(400).json({ error: 'Email et mot de passe requis' });

    const { data: user, error } = await supabase
      .from('user')
      .select('id, email, nom, role, password_hash')
      .eq('email', email.toLowerCase().trim())
      .single();

    if (error || !user) return res.status(401).json({ error: 'Identifiants invalides' });
    if (!verifyPassword(password, user.password_hash))
      return res.status(401).json({ error: 'Identifiants invalides' });

    const token = createToken(user.id, user.email, user.nom, user.role);
    return res.status(200).json({ token, nom: user.nom, role: user.role, email: user.email });
  }

  if (action === 'register') {
    const { email, password, nom, role } = req.body || {};
    if (!email || !password || !nom) return res.status(400).json({ error: 'Champs requis manquants' });

    const allowedRoles = ['prof', 'eleve'];
    const userRole = allowedRoles.includes(role) ? role : 'eleve';

    const { data: existing } = await supabase
      .from('user')
      .select('id')
      .eq('email', email.toLowerCase().trim())
      .single();

    if (existing) return res.status(409).json({ error: 'Email déjà utilisé' });

    const password_hash = hashPassword(password);

    const { data: user, error } = await supabase
      .from('user')
      .insert({ email: email.toLowerCase().trim(), password_hash, nom, role: userRole })
      .select('id, email, nom, role')
      .single();

    if (error) return res.status(500).json({ error: 'Erreur lors de la création du compte' });

    const token = createToken(user.id, user.email, user.nom, user.role);
    return res.status(201).json({ token, nom: user.nom, role: user.role, email: user.email });
  }

  return res.status(404).json({ error: 'Action inconnue' });
}
