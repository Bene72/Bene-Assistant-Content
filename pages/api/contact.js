import { supabase } from '../../lib/supabaseClient'

export default async function handler(req, res) {
  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Method not allowed' })
  }

  const { name, email, phone, message, service } = req.body

  if (!name || !email || !message) {
    return res.status(400).json({ error: 'Champs obligatoires manquants.' })
  }

  const { error } = await supabase
    .from('contacts')
    .insert([{ name, email, phone, message, service, created_at: new Date().toISOString() }])

  if (error) {
    console.error('Supabase error:', error)
    return res.status(500).json({ error: 'Erreur lors de l\'enregistrement.' })
  }

  return res.status(200).json({ success: true })
}
