import { useEffect, useRef, useState } from 'react'
import Markdown from 'react-markdown'
import remarkGfm from 'remark-gfm'

const MARKDOWN_COMPONENTS = {
  table: ({ children }) => (
    <div className="studio-markdown-table">
      <table>{children}</table>
    </div>
  ),
}

const COPY = {
  es: {
    heading: 'Un portfolio de AI Engineering',
    description: 'Pregunta por la experiencia de Adrián en IA, datos, software y proyectos.',
    portraitAlt: 'Retrato de Adrián Amaro al aire libre.',
    welcome:
      'Hola, soy el asistente del portfolio de Adrián. Puedes preguntarme sobre su experiencia, proyectos y herramientas de IA, datos y software. Estoy aquí para facilitar tu revisión para puestos de AI Engineer, con respuestas basadas en su CV.',
    suggested: 'Empieza por aquí',
    questions: [
      {
        label: 'Trayectoria profesional',
        question: '¿Qué experiencia y trayectoria profesional aporta Adrián para un puesto de AI Engineer?',
      },
      { label: 'Datos y Spark', question: '¿Qué ha hecho con Spark y procesamiento de datos?' },
      { label: 'Este asistente', question: '¿Cómo funciona este asistente de portfolio?' },
    ],
    placeholder: 'Escribe una pregunta sobre Adrián…',
    inputLabel: 'Tu pregunta',
    send: 'Enviar',
    assistant: 'Asistente',
    you: 'Tú',
    loading: 'Preparando respuesta',
    sending: 'Enviando',
    error: 'No se pudo completar la respuesta. Revisa tu conexión e inténtalo de nuevo.',
    retry: 'Reintentar',
  },
  en: {
    heading: 'AI engineering portfolio',
    description: "Ask about Adrián's experience in AI, data, software, and projects.",
    portraitAlt: 'Portrait of Adrián Amaro outdoors.',
    welcome:
      "Hi, I'm Adrián's portfolio assistant. Ask about his experience, projects, and AI, data, or software tools. I'm here to make reviewing his profile for AI Engineer roles easier, with answers grounded in his CV.",
    suggested: 'Start here',
    questions: [
      {
        label: 'Career experience',
        question: 'What experience and career background does Adrián bring to an AI Engineer role?',
      },
      { label: 'Data & Spark', question: 'What has he done with Spark and data processing?' },
      { label: 'This assistant', question: 'How does this portfolio assistant work?' },
    ],
    placeholder: 'Ask a question about Adrián…',
    inputLabel: 'Your question',
    send: 'Send',
    assistant: 'Assistant',
    you: 'You',
    loading: 'Preparing an answer',
    sending: 'Sending',
    error: "The answer couldn't be completed. Check your connection and try again.",
    retry: 'Try again',
  },
}

const MAX_HISTORY_MESSAGES = 22

export default function Chat({ language, profile, profileId }) {
  const copy = COPY[language]
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState(false)
  const [threadId] = useState(() => crypto.randomUUID())
  const conversationHistory = useRef([])
  const bottomRef = useRef(null)
  const textareaRef = useRef(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' })
  }, [messages])

  function appendToken(token) {
    setMessages((previous) => {
      const next = [...previous]
      const last = next.at(-1)
      if (last?.role === 'assistant') {
        next[next.length - 1] = { ...last, content: last.content + token }
      }
      return next
    })
  }

  function removeEmptyAssistant() {
    setMessages((previous) => {
      const next = [...previous]
      if (next.at(-1)?.role === 'assistant' && !next.at(-1).content) next.pop()
      return next
    })
  }

  async function send(text, { retry = false } = {}) {
    const message = text.trim()
    if (!message || busy) return
    const history = conversationHistory.current.slice(-MAX_HISTORY_MESSAGES)

    setError(false)
    setInput('')
    if (textareaRef.current) textareaRef.current.style.height = ''
    setBusy(true)
    setMessages((previous) => {
      const retryIndex = retry
        ? previous.findLastIndex(
            (item) => item.role === 'user' && item.content === message,
          )
        : -1
      const withoutRetriedQuestion =
        retryIndex >= 0 ? previous.slice(0, retryIndex) : previous

      return [
        ...withoutRetriedQuestion,
        { role: 'user', content: message },
        { role: 'assistant', content: '' },
      ]
    })

    try {
      const response = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message,
          thread_id: threadId,
          profile_id: profileId,
          history,
        }),
      })
      if (!response.ok || !response.body) throw new Error(`HTTP ${response.status}`)

      const reader = response.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''
      let answer = ''
      let completed = false
      for (;;) {
        const { done, value } = await reader.read()
        if (done) break
        buffer += decoder.decode(value, { stream: true })
        const events = buffer.split('\n\n')
        buffer = events.pop() ?? ''
        for (const event of events) {
          const line = event.trim()
          if (!line.startsWith('data: ')) continue
          const payload = JSON.parse(line.slice(6))
          if (payload.error) throw new Error(payload.error)
          if (payload.restart) {
            answer = ''
            setMessages((previous) => {
              const next = [...previous]
              const last = next.at(-1)
              if (last?.role === 'assistant') {
                next[next.length - 1] = { ...last, content: '' }
              }
              return next
            })
          }
          if (payload.token) {
            answer += payload.token
            appendToken(payload.token)
          }
          if (payload.done) completed = true
        }
      }
      if (!completed || !answer) throw new Error('The response stream ended early')
      conversationHistory.current = [
        ...history,
        { role: 'user', content: message },
        { role: 'assistant', content: answer },
      ].slice(-MAX_HISTORY_MESSAGES)
    } catch {
      setError(true)
      removeEmptyAssistant()
    } finally {
      setBusy(false)
    }
  }

  const lastQuestion = [...messages].reverse().find((message) => message.role === 'user')?.content
  const empty = messages.length === 0
  const welcome = profile?.welcome?.[language] ?? copy.welcome
  const questions = profile?.questions?.[language] ?? copy.questions
  const heading = copy.heading
  const description = profile?.positioning?.[language] ?? copy.description

  return (
    <section className="studio-chat" aria-labelledby="chat-title">
      <div className={`studio-chat-opening${empty ? '' : ' studio-chat-opening--active'}`}>
        <header className="studio-chat-heading">
          <div className="studio-chat-title-group">
            <h1 id="chat-title">{heading}</h1>
            <Markdown remarkPlugins={[remarkGfm]}>{description}</Markdown>
          </div>
        </header>

        {empty && (
          <div className="studio-welcome-copy">
            <span className="studio-welcome-author">{copy.assistant}</span>
            <p>{welcome}</p>
          </div>
        )}

        <figure className="studio-chat-portrait">
          <img
            src="/images/adrian-amaro-profile.webp"
            alt={copy.portraitAlt}
            fetchPriority="high"
            decoding="async"
          />
          <figcaption>Adrián Amaro</figcaption>
        </figure>

        <div className="studio-starters">
          {empty && <h2>{copy.suggested}</h2>}
          <ul>
            {questions.map(({ label, question }) => (
              <li key={label}>
                <button
                  type="button"
                  title={question}
                  aria-label={question}
                  onClick={() => send(question)}
                  disabled={busy}
                >
                  <span>{label}</span>
                  <svg viewBox="0 0 20 20" fill="none" aria-hidden="true">
                    <path d="M3 10h13m-5-5 5 5-5 5" />
                  </svg>
                </button>
              </li>
            ))}
          </ul>
        </div>
      </div>

      <div className="studio-conversation" role="log" aria-label={heading} aria-live="polite">
        <div className="studio-message-list">
          {messages.map((message, index) => (
            <article className={`studio-message studio-message--${message.role}`} key={`${index}-${message.role}`}>
              <h2 className="studio-message-author">
                {message.role === 'user' ? copy.you : copy.assistant}
              </h2>
              {message.role === 'assistant' ? (
                <div className="studio-message-content">
                  {message.content ? (
                    <Markdown remarkPlugins={[remarkGfm]} components={MARKDOWN_COMPONENTS}>
                      {message.content}
                    </Markdown>
                  ) : (
                    <Loading copy={copy} />
                  )}
                </div>
              ) : (
                <p className="studio-message-content">{message.content}</p>
              )}
            </article>
          ))}
        </div>

        {error && (
          <div className="studio-chat-error" role="alert">
            <p>{copy.error}</p>
            {lastQuestion && (
              <button type="button" onClick={() => send(lastQuestion, { retry: true })}>
                {copy.retry}
              </button>
            )}
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      <div className="studio-composer-dock">
        <form
          className="studio-composer"
          onSubmit={(event) => {
            event.preventDefault()
            send(input)
          }}
        >
          <label className="studio-visually-hidden" htmlFor="chat-input">
            {copy.inputLabel}
          </label>
          <textarea
            id="chat-input"
            className="studio-composer-input"
            ref={textareaRef}
            rows={1}
            maxLength={4000}
            value={input}
            onChange={(event) => {
              setInput(event.target.value)
              event.target.style.height = 'auto'
              event.target.style.height = `${Math.min(event.target.scrollHeight, 144)}px`
            }}
            onKeyDown={(event) => {
              if (event.key === 'Enter' && !event.shiftKey) {
                event.preventDefault()
                send(input)
              }
            }}
            placeholder={copy.placeholder}
            disabled={busy}
          />
          <button className="studio-send-button" type="submit" disabled={busy || !input.trim()}>
            <span>{busy ? copy.sending : copy.send}</span>
            {!busy && (
              <svg viewBox="0 0 20 20" fill="none" aria-hidden="true">
                <path d="M3 10h13m-5-5 5 5-5 5" />
              </svg>
            )}
          </button>
        </form>
        <p className="studio-composer-note">
          {language === 'es' ? 'Intro para enviar · Mayús + Intro para saltar de línea' : 'Enter to send · Shift + Enter for a new line'}
        </p>
      </div>
    </section>
  )
}

function Loading({ copy }) {
  return (
    <span className="loading-answer" role="status" aria-label={copy.loading}>
      <span />
      <span />
      <span />
    </span>
  )
}
