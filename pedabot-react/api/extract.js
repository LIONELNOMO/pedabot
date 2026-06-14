import { IncomingForm } from 'formidable';
import fs from 'fs';
import pdfParse from 'pdf-parse';
import mammoth from 'mammoth';
import { cors } from '../lib/auth.js';

export const config = { api: { bodyParser: false } };

export default async function handler(req, res) {
  cors(res);
  if (req.method === 'OPTIONS') return res.status(200).end();
  if (req.method !== 'POST') return res.status(405).json({ detail: 'Method not allowed' });

  const form = new IncomingForm({ maxFileSize: 10 * 1024 * 1024 });

  form.parse(req, async (err, fields, files) => {
    if (err) return res.status(400).json({ detail: 'Erreur lecture fichier' });

    const file = Array.isArray(files.file) ? files.file[0] : files.file;
    if (!file) return res.status(400).json({ detail: 'Aucun fichier reçu' });

    const ext = file.originalFilename?.split('.').pop()?.toLowerCase();
    const buffer = fs.readFileSync(file.filepath);

    try {
      let text = '';
      if (ext === 'pdf') {
        const data = await pdfParse(buffer);
        text = data.text;
      } else if (ext === 'docx') {
        const result = await mammoth.extractRawText({ buffer });
        text = result.value;
      } else if (ext === 'txt') {
        text = buffer.toString('utf-8');
      } else {
        return res.status(400).json({ detail: 'Format non supporté (pdf, docx, txt uniquement)' });
      }

      text = text.trim();
      if (!text) return res.status(422).json({ detail: 'Fichier vide ou illisible' });

      return res.status(200).json({ text });
    } catch (e) {
      return res.status(500).json({ detail: 'Erreur extraction texte' });
    } finally {
      try { fs.unlinkSync(file.filepath); } catch {}
    }
  });
}
