import { useEffect, useRef, useState } from 'react'
import Markdown from 'react-markdown'

const COPY = {
  es: {
    heading: 'Un portfolio de AI Engineering',
    description: 'Pregunta por la experiencia de Adrián en IA, datos, software y proyectos.',
    welcome:
      'Hola, soy el asistente del portfolio de Adrián. Puedes preguntarme sobre su experiencia, proyectos y herramientas de IA, datos y software. Estoy aquí para facilitar tu revisión para puestos de AI Engineer, con respuestas basadas en su CV.',
    suggested: 'Empieza por aquí',
    questions: [
      { label: 'IA y LangChain', question: '¿Qué experiencia tiene con IA y LangChain?' },
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
    heading: 'An AI engineering portfolio',
    description: "Ask about Adrián's experience in AI, data, software, and projects.",
    welcome:
      "Hi, I'm Adrián's portfolio assistant. Ask about his experience, projects, and AI, data, or software tools. I'm here to make reviewing his profile for AI Engineer roles easier, with answers grounded in his CV.",
    suggested: 'Start here',
    questions: [
      { label: 'AI & LangChain', question: 'What experience does he have with AI and LangChain?' },
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

function getThreadId() {
  let id = localStorage.getItem('thread_id')
  if (!id) {
    id = crypto.randomUUID()
    localStorage.setItem('thread_id', id)
  }
  return id
}

export default function Chat({ language }) {
  const copy = COPY[language]
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState(false)
  const [threadId] = useState(getThreadId)
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

  async function send(text) {
    const message = text.trim()
    if (!message || busy) return

    setError(false)
    setInput('')
    if (textareaRef.current) textareaRef.current.style.height = ''
    setBusy(true)
    setMessages((previous) => [
      ...previous,
      { role: 'user', content: message },
      { role: 'assistant', content: '' },
    ])

    try {
      const response = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message, thread_id: threadId }),
      })
      if (!response.ok || !response.body) throw new Error(`HTTP ${response.status}`)

      const reader = response.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''
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
            setMessages((previous) => {
              const next = [...previous]
              const last = next.at(-1)
              if (last?.role === 'assistant') {
                next[next.length - 1] = { ...last, content: '' }
              }
              return next
            })
          }
          if (payload.token) appendToken(payload.token)
        }
      }
    } catch {
      setError(true)
      removeEmptyAssistant()
    } finally {
      setBusy(false)
    }
  }

  const lastQuestion = [...messages].reverse().find((message) => message.role === 'user')?.content
  const empty = messages.length === 0

  return (
    <section className="studio-chat" aria-labelledby="chat-title">
      <header className="studio-chat-heading">
        <div className="studio-chat-title-group">
          <h1 id="chat-title">{copy.heading}</h1>
          <p>{copy.description}</p>
        </div>
        <svg className="studio-chat-mark" viewBox="0 0 104 104" fill="none" aria-hidden="true">
          <path d="M8 67c10-10 20-10 30 0s20 10 30 0 20-10 28 0" />
          <path d="M8 51c10-10 20-10 30 0s20 10 30 0 20-10 28 0" />
          <path d="M8 35c10-10 20-10 30 0s20 10 30 0 20-10 28 0" />
          <circle cx="83" cy="20" r="4" />
        </svg>
      </header>

      <div className="studio-conversation" role="log" aria-label={copy.heading} aria-live="polite">
        {empty && (
          <div className="studio-welcome">
            <span className="studio-welcome-author">{copy.assistant}</span>
            <p>{copy.welcome}</p>
            <div className="studio-starters">
              <h2>{copy.suggested}</h2>
              <ul>
                {copy.questions.map(({ label, question }) => (
                  <li key={label}>
                    <button type="button" onClick={() => send(question)} disabled={busy}>
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
        )}

        <div className="studio-message-list">
          {messages.map((message, index) => (
            <article className={`studio-message studio-message--${message.role}`} key={`${index}-${message.role}`}>
              <h2 className="studio-message-author">
                {message.role === 'user' ? copy.you : copy.assistant}
              </h2>
              {message.role === 'assistant' ? (
                <div className="studio-message-content">
                  {message.content ? <Markdown>{message.content}</Markdown> : <Loading copy={copy} />}
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
              <button type="button" onClick={() => send(lastQuestion)}>
                {copy.retry}
              </button>
            )}
          </div>
        )}
        <div ref={bottomRef} />
      </div>

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
