import Head from 'next/head'
import { useState } from 'react'

const SERVICES = [
  {
    icon: '⚡',
    title: 'Coaching Individuel',
    desc: 'Un programme 100 % sur mesure adapté à ton corps, ton rythme et tes objectifs.',
    price: 'À partir de 60 €/séance',
  },
  {
    icon: '🏋️',
    title: 'Suivi Mensuel',
    desc: 'Plan d\'entraînement + nutrition + check-in hebdomadaire pour progresser en continu.',
    price: 'À partir de 150 €/mois',
  },
  {
    icon: '🎯',
    title: 'Programme Transforme-toi',
    desc: '12 semaines de transformation complète : corpo, cardio, alimentation et mental.',
    price: 'À partir de 490 €',
  },
]

const TESTIMONIALS = [
  {
    name: 'Sophie M.',
    result: '−12 kg en 3 mois',
    text: 'Ben a totalement changé ma vision du sport. J\'ai enfin trouvé un rythme qui me correspond et les résultats sont au rendez-vous.',
    initials: 'SM',
  },
  {
    name: 'Thomas R.',
    result: '+8 kg de muscle',
    text: 'Programme ultra précis, disponibilité exemplaire. Je recommande à 100 % à quiconque veut vraiment changer.',
    initials: 'TR',
  },
  {
    name: 'Lucie D.',
    result: 'Marathon en 4h02',
    text: 'Je n\'aurais jamais pensé finir un marathon. Ben a cru en moi avant que j\'y croie moi-même.',
    initials: 'LD',
  },
]

const FAQ = [
  {
    q: 'Est-ce que tu travailles avec des débutants ?',
    a: 'Absolument. La majorité de mes clients partent de zéro. Je m\'adapte entièrement à ton niveau actuel.',
  },
  {
    q: 'Les séances sont-elles en présentiel ou en ligne ?',
    a: 'Les deux ! Je propose des séances à domicile (Bretagne), en salle, ou entièrement en ligne via visio.',
  },
  {
    q: 'Est-ce que tu proposes un suivi nutritionnel ?',
    a: 'Oui, tous mes forfaits incluent des conseils nutritionnels personnalisés. Je ne suis pas diététicien, mais je t\'accompagne avec des bases solides et efficaces.',
  },
  {
    q: 'Comment se passe le premier contact ?',
    a: 'Tu remplis le formulaire ci-dessous, je te rappelle sous 24 h pour un bilan gratuit de 20 minutes sans engagement.',
  },
]

export default function Home() {
  const [form, setForm] = useState({ name: '', email: '', phone: '', service: '', message: '' })
  const [status, setStatus] = useState(null) // null | 'loading' | 'success' | 'error'
  const [openFaq, setOpenFaq] = useState(null)

  const handleChange = e => setForm(f => ({ ...f, [e.target.name]: e.target.value }))

  const handleSubmit = async e => {
    e.preventDefault()
    setStatus('loading')
    try {
      const res = await fetch('/api/contact', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(form),
      })
      const data = await res.json()
      if (data.success) {
        setStatus('success')
        setForm({ name: '', email: '', phone: '', service: '', message: '' })
      } else {
        setStatus('error')
      }
    } catch {
      setStatus('error')
    }
  }

  return (
    <>
      <Head>
        <title>Ben&Fit — Coaching Sportif Premium</title>
        <meta name="description" content="Coaching sportif et fitness personnalisé avec Ben&Fit. Transforme ton corps, dépasse tes limites." />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <link rel="icon" href="/favicon.ico" />
      </Head>

      {/* ── NAVIGATION ── */}
      <header className="fixed top-0 w-full z-50 bg-white/95 backdrop-blur border-b border-stone-100">
        <div className="max-w-6xl mx-auto px-6 h-16 flex items-center justify-between">
          <a href="#" className="font-serif text-xl font-bold tracking-tight">
            Ben<span style={{ color: 'var(--gold)' }}>&</span>Fit
          </a>
          <nav className="hidden md:flex items-center gap-8 text-sm font-medium text-stone-600">
            <a href="#services">Services</a>
            <a href="#apropos">À propos</a>
            <a href="#temoignages">Témoignages</a>
            <a href="#faq">FAQ</a>
          </nav>
          <a
            href="#contact"
            className="text-sm font-semibold px-5 py-2 rounded-full text-white transition-opacity hover:opacity-90"
            style={{ background: 'var(--gold)' }}
          >
            Bilan gratuit
          </a>
        </div>
      </header>

      <main>
        {/* ── HERO ── */}
        <section
          id="hero"
          className="relative min-h-screen flex items-center justify-center text-center px-6 pt-20"
          style={{
            background: 'linear-gradient(160deg, #FFFBF0 0%, #ffffff 55%, #FFFBF0 100%)',
          }}
        >
          {/* Decorative circle */}
          <div
            className="absolute right-10 top-32 w-72 h-72 rounded-full opacity-10 pointer-events-none"
            style={{ background: 'var(--gold)', filter: 'blur(80px)' }}
          />
          <div className="relative max-w-3xl mx-auto">
            <p className="fade-up text-xs font-semibold tracking-[0.2em] uppercase mb-4" style={{ color: 'var(--gold)' }}>
              Coaching sportif & fitness
            </p>
            <h1 className="fade-up delay-1 font-serif text-5xl md:text-7xl font-bold leading-tight text-stone-900 mb-6">
              Sculpte le meilleur<br />
              <em className="font-serif font-normal" style={{ color: 'var(--gold)' }}>version de toi</em>
            </h1>
            <p className="fade-up delay-2 text-lg text-stone-500 leading-relaxed mb-10 max-w-xl mx-auto">
              Programmes personnalisés, suivi humain et résultats durables. Peu importe ton point de départ, on avance ensemble.
            </p>
            <div className="fade-up delay-3 flex flex-col sm:flex-row gap-4 justify-center">
              <a
                href="#contact"
                className="inline-flex items-center gap-2 px-8 py-3.5 rounded-full font-semibold text-white shadow-lg transition-all hover:scale-105"
                style={{ background: 'var(--gold)' }}
              >
                Bilan gratuit 20 min →
              </a>
              <a
                href="#services"
                className="inline-flex items-center gap-2 px-8 py-3.5 rounded-full font-semibold text-stone-700 border border-stone-200 hover:border-stone-400 transition-colors"
              >
                Voir les formules
              </a>
            </div>
            {/* Stats row */}
            <div className="fade-up delay-4 mt-16 flex flex-col sm:flex-row justify-center gap-10 text-center">
              {[['+ 120', 'clients accompagnés'], ['97 %', 'taux de satisfaction'], ['5 ans', 'd\'expérience']].map(([num, label]) => (
                <div key={label}>
                  <p className="font-serif text-3xl font-bold text-stone-900">{num}</p>
                  <p className="text-sm text-stone-400 mt-1">{label}</p>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* ── SERVICES ── */}
        <section id="services" className="py-24 px-6 bg-white">
          <div className="max-w-6xl mx-auto">
            <div className="text-center mb-16">
              <p className="text-xs font-semibold tracking-[0.2em] uppercase mb-3" style={{ color: 'var(--gold)' }}>Formules</p>
              <h2 className="font-serif text-4xl font-bold text-stone-900 mb-4">Mes services</h2>
              <div className="gold-line mx-auto" />
            </div>
            <div className="grid md:grid-cols-3 gap-8">
              {SERVICES.map((s, i) => (
                <div
                  key={s.title}
                  className="group relative rounded-2xl p-8 border border-stone-100 hover:shadow-xl transition-all duration-300 hover:-translate-y-1"
                  style={i === 1 ? { background: '#FFFBF0', borderColor: '#D4A017' } : { background: '#fff' }}
                >
                  {i === 1 && (
                    <span className="absolute -top-3 left-1/2 -translate-x-1/2 text-xs font-semibold px-4 py-1 rounded-full text-white" style={{ background: 'var(--gold)' }}>
                      Le plus populaire
                    </span>
                  )}
                  <div className="text-3xl mb-4">{s.icon}</div>
                  <h3 className="font-serif text-xl font-bold text-stone-900 mb-3">{s.title}</h3>
                  <p className="text-stone-500 text-sm leading-relaxed mb-6">{s.desc}</p>
                  <p className="font-semibold text-sm" style={{ color: 'var(--gold-dark)' }}>{s.price}</p>
                  <a
                    href="#contact"
                    className="mt-6 block text-center text-sm font-semibold py-2.5 rounded-full border transition-all hover:text-white"
                    style={i === 1
                      ? { background: 'var(--gold)', color: '#fff', borderColor: 'var(--gold)' }
                      : { borderColor: '#e7e5e4', color: '#57534e' }}
                    onMouseEnter={e => { if (i !== 1) { e.target.style.background = 'var(--gold)'; e.target.style.color = '#fff'; e.target.style.borderColor = 'var(--gold)' } }}
                    onMouseLeave={e => { if (i !== 1) { e.target.style.background = ''; e.target.style.color = '#57534e'; e.target.style.borderColor = '#e7e5e4' } }}
                  >
                    Me contacter
                  </a>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* ── À PROPOS ── */}
        <section id="apropos" className="py-24 px-6" style={{ background: '#FAFAF8' }}>
          <div className="max-w-6xl mx-auto grid md:grid-cols-2 gap-16 items-center">
            <div>
              <p className="text-xs font-semibold tracking-[0.2em] uppercase mb-3" style={{ color: 'var(--gold)' }}>À propos</p>
              <h2 className="font-serif text-4xl font-bold text-stone-900 mb-6">
                Coach certifié,<br /><em className="font-serif font-normal">passionné de résultats</em>
              </h2>
              <div className="gold-line mb-6" />
              <p className="text-stone-500 leading-relaxed mb-4">
                Je m'appelle Ben. Depuis plus de 5 ans, j'accompagne hommes et femmes de tous âges à transformer leur corps et leur relation au sport.
              </p>
              <p className="text-stone-500 leading-relaxed mb-4">
                Certifié BPJEPS, formé en nutrition sportive et en préparation mentale, je construis des programmes qui s'adaptent à <strong className="font-medium text-stone-700">ta vie réelle</strong> — pas l'inverse.
              </p>
              <p className="text-stone-500 leading-relaxed">
                Basé en Bretagne, j'interviens à domicile, en salle, ou à distance partout en France.
              </p>
              <div className="mt-8 flex flex-wrap gap-3">
                {['BPJEPS Fitness', 'Nutrition sportive', 'Préparation mentale', 'CrossFit L1'].map(b => (
                  <span key={b} className="text-xs font-medium px-4 py-2 rounded-full border" style={{ borderColor: '#D4A017', color: '#A87B0E', background: '#FFFBF0' }}>
                    {b}
                  </span>
                ))}
              </div>
            </div>
            {/* Photo placeholder */}
            <div className="relative">
              <div
                className="w-full aspect-[4/5] rounded-2xl flex flex-col items-center justify-center text-center p-8"
                style={{ background: 'linear-gradient(145deg, #FEF3CC, #FFFBF0)', border: '1px solid #FDE89A' }}
              >
                <div className="w-24 h-24 rounded-full flex items-center justify-center mb-4 text-4xl" style={{ background: '#D4A017' }}>
                  💪
                </div>
                <p className="font-serif text-2xl font-bold text-stone-800">Ben</p>
                <p className="text-stone-500 text-sm mt-1">Coach Ben&Fit</p>
                <p className="text-xs mt-4 text-stone-400 italic">
                  Remplace ce bloc par ta vraie photo<br />dans le code (voir guide)
                </p>
              </div>
              <div
                className="absolute -bottom-4 -right-4 w-32 h-32 rounded-full opacity-20 pointer-events-none"
                style={{ background: 'var(--gold)', filter: 'blur(40px)' }}
              />
            </div>
          </div>
        </section>

        {/* ── TÉMOIGNAGES ── */}
        <section id="temoignages" className="py-24 px-6 bg-white">
          <div className="max-w-6xl mx-auto">
            <div className="text-center mb-16">
              <p className="text-xs font-semibold tracking-[0.2em] uppercase mb-3" style={{ color: 'var(--gold)' }}>Témoignages</p>
              <h2 className="font-serif text-4xl font-bold text-stone-900 mb-4">Ils ont transformé leur vie</h2>
              <div className="gold-line mx-auto" />
            </div>
            <div className="grid md:grid-cols-3 gap-8">
              {TESTIMONIALS.map(t => (
                <div key={t.name} className="rounded-2xl p-8 border border-stone-100 bg-white hover:shadow-lg transition-shadow">
                  <div className="flex items-center gap-3 mb-5">
                    <div
                      className="w-10 h-10 rounded-full flex items-center justify-center text-xs font-bold"
                      style={{ background: '#FEF3CC', color: '#A87B0E' }}
                    >
                      {t.initials}
                    </div>
                    <div>
                      <p className="font-semibold text-sm text-stone-800">{t.name}</p>
                      <p className="text-xs font-medium" style={{ color: 'var(--gold)' }}>{t.result}</p>
                    </div>
                  </div>
                  <div className="text-2xl mb-3" style={{ color: 'var(--gold)' }}>❝</div>
                  <p className="text-stone-500 text-sm leading-relaxed italic">{t.text}</p>
                  <div className="flex gap-1 mt-4">
                    {[...Array(5)].map((_, i) => <span key={i} style={{ color: 'var(--gold)' }}>★</span>)}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* ── FAQ ── */}
        <section id="faq" className="py-24 px-6" style={{ background: '#FAFAF8' }}>
          <div className="max-w-2xl mx-auto">
            <div className="text-center mb-14">
              <p className="text-xs font-semibold tracking-[0.2em] uppercase mb-3" style={{ color: 'var(--gold)' }}>FAQ</p>
              <h2 className="font-serif text-4xl font-bold text-stone-900 mb-4">Questions fréquentes</h2>
              <div className="gold-line mx-auto" />
            </div>
            <div className="space-y-3">
              {FAQ.map((item, i) => (
                <div key={i} className="rounded-xl border border-stone-200 bg-white overflow-hidden">
                  <button
                    className="w-full flex items-center justify-between px-6 py-4 text-left font-medium text-stone-800 hover:bg-stone-50 transition-colors"
                    onClick={() => setOpenFaq(openFaq === i ? null : i)}
                  >
                    <span>{item.q}</span>
                    <span className="ml-4 text-lg transition-transform" style={{ color: 'var(--gold)', transform: openFaq === i ? 'rotate(45deg)' : 'none' }}>+</span>
                  </button>
                  {openFaq === i && (
                    <div className="px-6 pb-5 text-sm text-stone-500 leading-relaxed border-t border-stone-100">
                      <div className="pt-4">{item.a}</div>
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* ── CONTACT / FORMULAIRE ── */}
        <section id="contact" className="py-24 px-6 bg-white">
          <div className="max-w-xl mx-auto">
            <div className="text-center mb-12">
              <p className="text-xs font-semibold tracking-[0.2em] uppercase mb-3" style={{ color: 'var(--gold)' }}>Contact</p>
              <h2 className="font-serif text-4xl font-bold text-stone-900 mb-4">Commence maintenant</h2>
              <p className="text-stone-500">Remplis ce formulaire et je te rappelle sous 24 h pour un bilan <strong className="font-medium text-stone-700">100 % gratuit et sans engagement</strong>.</p>
              <div className="gold-line mx-auto mt-4" />
            </div>

            {status === 'success' ? (
              <div className="text-center py-12 px-8 rounded-2xl" style={{ background: '#FFFBF0', border: '1px solid #FDE89A' }}>
                <div className="text-5xl mb-4">🎉</div>
                <p className="font-serif text-2xl font-bold text-stone-800 mb-2">Message reçu !</p>
                <p className="text-stone-500">Je te contacte dans les 24 h. À très vite !</p>
              </div>
            ) : (
              <form onSubmit={handleSubmit} className="space-y-5">
                <div className="grid sm:grid-cols-2 gap-5">
                  <div>
                    <label className="block text-xs font-medium text-stone-500 mb-1.5">Prénom & Nom *</label>
                    <input
                      type="text"
                      name="name"
                      value={form.name}
                      onChange={handleChange}
                      required
                      placeholder="Jean Dupont"
                      className="w-full px-4 py-3 rounded-xl border border-stone-200 text-sm text-stone-800 placeholder-stone-300"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-stone-500 mb-1.5">Email *</label>
                    <input
                      type="email"
                      name="email"
                      value={form.email}
                      onChange={handleChange}
                      required
                      placeholder="jean@email.com"
                      className="w-full px-4 py-3 rounded-xl border border-stone-200 text-sm text-stone-800 placeholder-stone-300"
                    />
                  </div>
                </div>
                <div>
                  <label className="block text-xs font-medium text-stone-500 mb-1.5">Téléphone</label>
                  <input
                    type="tel"
                    name="phone"
                    value={form.phone}
                    onChange={handleChange}
                    placeholder="06 00 00 00 00"
                    className="w-full px-4 py-3 rounded-xl border border-stone-200 text-sm text-stone-800 placeholder-stone-300"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-stone-500 mb-1.5">Service souhaité</label>
                  <select
                    name="service"
                    value={form.service}
                    onChange={handleChange}
                    className="w-full px-4 py-3 rounded-xl border border-stone-200 text-sm text-stone-700 bg-white"
                  >
                    <option value="">— Choisir une formule —</option>
                    <option value="individuel">Coaching Individuel</option>
                    <option value="mensuel">Suivi Mensuel</option>
                    <option value="transforme">Programme Transforme-toi (12 sem.)</option>
                    <option value="autre">Autre / Je ne sais pas encore</option>
                  </select>
                </div>
                <div>
                  <label className="block text-xs font-medium text-stone-500 mb-1.5">Ton objectif *</label>
                  <textarea
                    name="message"
                    value={form.message}
                    onChange={handleChange}
                    required
                    rows={4}
                    placeholder="Décris ton niveau actuel, ton objectif principal, et tout ce que tu penses utile…"
                    className="w-full px-4 py-3 rounded-xl border border-stone-200 text-sm text-stone-800 placeholder-stone-300 resize-none"
                  />
                </div>
                {status === 'error' && (
                  <p className="text-red-500 text-sm">Une erreur est survenue. Réessaie ou contacte-moi directement.</p>
                )}
                <button
                  type="submit"
                  disabled={status === 'loading'}
                  className="w-full py-4 rounded-full font-semibold text-white transition-all hover:opacity-90 hover:scale-[1.02] disabled:opacity-60"
                  style={{ background: 'var(--gold)' }}
                >
                  {status === 'loading' ? 'Envoi en cours…' : 'Envoyer ma demande de bilan gratuit →'}
                </button>
                <p className="text-center text-xs text-stone-400">Tes données sont confidentielles et ne sont jamais partagées.</p>
              </form>
            )}
          </div>
        </section>
      </main>

      {/* ── FOOTER ── */}
      <footer className="py-10 px-6 border-t border-stone-100 bg-white">
        <div className="max-w-6xl mx-auto flex flex-col md:flex-row items-center justify-between gap-4 text-sm text-stone-400">
          <span className="font-serif font-bold text-stone-700">
            Ben<span style={{ color: 'var(--gold)' }}>&</span>Fit
          </span>
          <span>© {new Date().getFullYear()} Ben&Fit — Coaching sportif. Tous droits réservés.</span>
          <div className="flex gap-6">
            <a href="#" className="hover:text-stone-600 transition-colors">Instagram</a>
            <a href="mailto:contact@benfit.fr" className="hover:text-stone-600 transition-colors">contact@benfit.fr</a>
          </div>
        </div>
      </footer>
    </>
  )
}
