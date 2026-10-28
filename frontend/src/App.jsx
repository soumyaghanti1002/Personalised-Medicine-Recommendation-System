
import { useEffect, useState } from 'react';

const API = 'http://127.0.0.1:5000/api';

const nav = [
    ['⌂', 'Dashboard'],
    ['♧', 'Symptom Checker'],
    ['◷', 'Health'],
    ['◌', 'AI Assistant'],
    ['♡', 'Diet'],
    ['✚', 'Medicines']
];

export default function App() {
    const [page, setPage] = useState('Dashboard');
    const [dash, setDash] = useState({
        totalChecks: 0,
        medicineCount: 0,
        chatCount: 0,
        recent: [],
        trends: []
    });
    const [meds, setMeds] = useState([]);
    const [diets, setDiets] = useState([]);
    const [symptoms, setSymptoms] = useState('');
    const [duration, setDuration] = useState('');
    const [result, setResult] = useState(null);
    const [message, setMessage] = useState('');
    const [chat, setChat] = useState([]);
    const [error, setError] = useState('');
    const [loading, setLoading] = useState(false);

    async function load() {
        try {
            const [d, m, di, c] = await Promise.all([
                fetch(API + '/dashboard').then(r => r.json()),
                fetch(API + '/medicines').then(r => r.json()),
                fetch(API + '/diet-recommendations').then(r => r.json()),
                fetch(API + '/chat').then(r => r.json())
            ]);

            if (d.error) throw Error(d.error);
            if (!Array.isArray(m)) throw Error(m.error || 'Could not load medicines.');
            if (!Array.isArray(di)) throw Error(di.error || 'Could not load diets.');
            if (!Array.isArray(c)) throw Error(c.error || 'Could not load chat.');

            setDash(d);
            setMeds(m);
            setDiets(di);
            setChat(c);
            setError('');
        } catch {
            setError('Cannot connect to Flask/MySQL. Start the backend and check backend/.env.');
        }
    }

    useEffect(() => {
        load();
    }, []);

    async function submit(e) {
        e.preventDefault();
        setError('');
        setResult(null);
        setLoading(true);

        try {
            const r = await fetch(API + '/symptom-checks', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ symptoms, duration })
            });

            const d = await r.json();

            if (!r.ok) {
                throw Error(d.error || 'Could not process symptoms.');
            }

            setResult(d.result);

            setSymptoms('');
            setDuration('');
            await load();
        } catch (e) {
            setError(e.message);
        } finally {
            setLoading(false);
        }
    }

    async function send(e) {
        e.preventDefault();

        if (!message.trim()) return;

        setError('');

        try {
            const r = await fetch(API + '/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message })
            });

            const d = await r.json();

            if (!r.ok) {
                throw Error(d.error || 'Could not send message.');
            }

            setChat(old => [...old, d.user, d.assistant]);
            setMessage('');
            await load();
        } catch (e) {
            setError(e.message);
        }
    }

    return (
        <div className="shell">
            <aside className="sidebar">
                <div className="brand">
                    <span>✚</span>
                    <b>
                        Personalised Medicine Recommendation System
                        {/* <small>Recommendation System</small> */}
                        <small>Your Personal Health Companion</small>
                    </b>
                </div>

                <p className="nav-label">MENU</p>

                {nav.map(([i, n]) => (
                    <button
                        key={n}
                        className={'nav ' + (page === n ? 'active' : '')}
                        onClick={() => setPage(n)}
                    >
                        <span>{i}</span>
                        {n}
                    </button>
                ))}

                <div className="note">
                    <b>Your health matters</b>
                    <p>Track your wellness journey in one place.</p>
                </div>
            </aside>

            <main className="main">
                <header>
                    <div>
                        <small>PERSONALISED MEDICINE / {page.toUpperCase()}</small>
                        <h1>
                            {page === 'Dashboard'
                                ? 'Your Health Dashboard'
                                : page}
                        </h1>
                        <p>
                            Track your health journey and personal wellness information.
                        </p>
                    </div>
                    <span className="avatar">P</span>
                </header>

                {error && <div className="alert">{error}</div>}

                {page === 'Dashboard' && (
                    <>
                        <div className="stats">
                            <Stat title="Total Health Checks" value={dash.totalChecks} icon="♧" />
                            <Stat title="Medicines Listed" value={dash.medicineCount} icon="⌁" />
                            <Stat title="AI Conversations" value={dash.chatCount} icon="◌" />
                        </div>

                        <div className="columns">
                            <section className="panel">
                                <h2>Quick Actions</h2>
                                <Action
                                    title="Check Symptoms"
                                    detail="Save a symptom check"
                                    onClick={() => setPage('Symptom Checker')}
                                />
                                <Action
                                    title="Ask Health Assistant"
                                    detail="General wellness guidance"
                                    onClick={() => setPage('AI Assistant')}
                                />
                                <Action
                                    title="Browse Medicines"
                                    detail="Explore the catalogue"
                                    onClick={() => setPage('Medicines')}
                                />
                            </section>

                            <section className="panel">
                                <h2>Symptom Trends</h2>
                                {dash.trends.length ? (
                                    <div className="bars">
                                        {dash.trends.map(t => (
                                            <div key={t.day} className="barcol">
                                                <div
                                                    className="bar"
                                                    style={{
                                                        height: Math.max(
                                                            8,
                                                            Math.min(100, t.count * 22)
                                                        ) + 'px'
                                                    }}
                                                />
                                                <small>{String(t.day).slice(5)}</small>
                                            </div>
                                        ))}
                                    </div>
                                ) : (
                                    <Empty
                                        title="No symptom data yet"
                                        detail="Save a check to see trends here."
                                    />
                                )}
                            </section>
                        </div>

                        <section className="panel">
                            <h2>Recent Activity</h2>
                            {dash.recent.length ? (
                                dash.recent.map(r => (
                                    <p className="activity" key={r.id}>
                                        <b>{r.title}</b> — {r.detail}
                                    </p>
                                ))
                            ) : (
                                <Empty
                                    title="No activity yet"
                                    detail="Your health activity will appear here."
                                />
                            )}
                        </section>
                    </>
                )}

                {page === 'Symptom Checker' && (
                    <section className="panel narrow">
                        <h2>Check Symptoms</h2>
                        <p>Enter symptoms such as headache, fever, cough, or fatigue.</p>

                        <form onSubmit={submit} className="form">
                            <label>
                                Symptoms
                                <textarea
                                    required
                                    minLength={3}
                                    value={symptoms}
                                    onChange={e => setSymptoms(e.target.value)}
                                    placeholder="e.g. headache, fever, cough"
                                />
                            </label>

                            <label>
                                Duration
                                <select
                                    value={duration}
                                    onChange={e => setDuration(e.target.value)}
                                >
                                    <option value="">Choose duration (optional)</option>
                                    <option>Today</option>
                                    <option>1–3 days</option>
                                    <option>4–7 days</option>
                                    <option>More than a week</option>
                                </select>
                            </label>

                            <button className="primary" type="submit" disabled={loading}>
                                {loading ? 'Processing...' : 'Check Symptoms'}
                            </button>
                        </form>

                        {result && (
  <div className="result">
    <p><b>Matched symptoms:</b> {result.matched.join(', ')}</p>
    {result.unmatched.length > 0 && (
      <p><small>Not recognised: {result.unmatched.join(', ')}</small></p>
    )}
    {result.predictions.map((p, i) => (
      <section className="panel" key={p.disease}>
        <small className="pill">{i === 0 ? 'Most likely' : 'Also possible'} · {p.confidence}%</small>
        <h2>{p.disease}</h2>
        <p>{p.description}</p>
        {i === 0 && (
          <>
            <p><b>Medications (from dataset):</b> {p.medications.join(', ')}</p>
            <p><b>Diet:</b> {p.diets.join(', ')}</p>
            <p><b>Precautions:</b> {p.precautions.join(', ')}</p>
          </>
        )}
      </section>
    ))}
  </div>
)}

                        <p className="disclaimer">
                            Educational machine learning demonstration only.
                            Predictions are not medical diagnoses or treatment
                            recommendations. Consult a qualified healthcare professional.
                        </p>
                    </section>
                )}

                {page === 'Health' && (
                    <section className="panel">
                        <h2>Health Overview</h2>
                        {dash.recent.length ? (
                            dash.recent.map(r => (
                                <p className="activity" key={r.id}>
                                    {r.title} — {r.detail}
                                </p>
                            ))
                        ) : (
                            <Empty
                                title="No health activity yet"
                                detail="Save a symptom check to begin your log."
                            />
                        )}
                    </section>
                )}

                {page === 'AI Assistant' && (
                    <section className="panel">
                        <h2>Personal Health Assistant</h2>
                        <div className="chat">
                            {chat.map(c => (
                                <div key={c.id} className={'bubble ' + c.role}>
                                    <small>
                                        {c.role === 'user'
                                            ? 'You'
                                            : 'Personal Health Assistant'}
                                    </small>
                                    <p>{c.message}</p>
                                </div>
                            ))}
                        </div>

                        <form className="chatform" onSubmit={send}>
                            <input
                                value={message}
                                onChange={e => setMessage(e.target.value)}
                                placeholder="Ask a general wellness question"
                            />
                            <button className="primary" type="submit">Send</button>
                        </form>
                    </section>
                )}

                {page === 'Diet' && (
                    <div className="cards">
                        {diets.map(d => (
                            <section className="panel" key={d.id}>
                                <small className="pill">{d.category}</small>
                                <h2>{d.title}</h2>
                                <p>{d.description}</p>
                            </section>
                        ))}
                    </div>
                )}

                {page === 'Medicines' && (
                    <div className="cards">
                        {meds.map(m => (
                            <section className="panel" key={m.id}>
                                <small className="pill">{m.category}</small>
                                <h2>{m.name}</h2>
                                <p>{m.description}</p>
                                <p className="disclaimer">{m.usageNote}</p>
                            </section>
                        ))}
                    </div>
                )}

                <footer>
                    Student project · Not a substitute for professional medical care
                </footer>
            </main>
        </div>
    );
}

function Stat({ title, value, icon }) {
    return (
        <section className="stat">
            <div>
                <p>{title}</p>
                <strong>{value ?? 0}</strong>
            </div>
            <span>{icon}</span>
        </section>
    );
}

function Action({ title, detail, onClick }) {
    return (
        <button className="action" onClick={onClick}>
            <span>
                <b>{title}</b>
                <small>{detail}</small>
            </span>
            <i>→</i>
        </button>
    );
}

function Empty({ title, detail }) {
    return (
        <div className="empty">
            <b>{title}</b>
            <p>{detail}</p>
        </div>
    );
}
