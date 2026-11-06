import { useEffect, useState } from 'react'
import Chat from './components/Chat.jsx'

const COPY = {
  es: {
    languageLabel: 'Idioma',
    focus: 'AI Engineer',
    location: 'Madrid',
    bannerAlt: 'Paisaje panorámico pintado de un camino entre campos y árboles.',
    linkedIn: 'LinkedIn',
    introduction: 'Ingeniero de software con más de tres años de experiencia en integración de LLM, pipelines de datos y sistemas backend distribuidos.',
    experience: 'Experiencia',
    trcRole:
      'Servicios backend con Spring Boot y flujos asíncronos en sistemas distribuidos.',
    role41ops:
      'Servidores MCP para flujos de trabajo empresariales con LLMs, microservicios con Java y Spring Boot, y procesamiento de datos con Spark.',
    siCongresosRole:
      'Servicios backend con Spring Boot, aplicaciones web y mantenimiento y migración de sistemas.',
    skills: 'Áreas de trabajo',
    backend: 'Backend',
    dataEngineering: 'Datos',
    aiEngineering: 'IA aplicada',
    development: 'Formación profesional',
    courseTitle: 'AI Agents Course — Hugging Face',
    courseCompletion: 'Completado en 2026',
    courseDescription:
      'Fundamentos de LLM, herramientas y function calling; ciclo razonamiento–acción–observación; smolagents, LlamaIndex y LangGraph; Agentic RAG, monitorización y evaluación de agentes.',
    profileTitle: 'Mi experiencia',
    profileNote: 'CV y herramientas',
    openDetails: 'Ver detalles',
    closeDetails: 'Ocultar detalles',
    flowTitle: 'Cómo funciona',
    assistantNote: 'Un vistazo al sistema que responde detrás del chat.',
    flowDisclaimer: 'Esquema estático del flujo implementado; no muestra actividad en vivo.',
    stages: [
      ['Pregunta → API', 'React y Vite envían tu pregunta a FastAPI.'],
      ['Revisión de entrada', 'Un clasificador revisa el mensaje antes de responder.'],
      ['Agente con contexto', 'LangGraph usa el CV y las notas del proyecto para preparar la respuesta.'],
      ['Revisión → chat', 'Solo la respuesta aprobada se transmite al chat por SSE.'],
    ],
    stackTitle: 'Tecnologías',
    deploymentTitle: 'Despliegue',
    deploymentNote:
      'Vercel sirve la interfaz React/Vite y reenvía /api/* a FastAPI en Cloud Run. Cloud Run puede escalar a cero; el CV y los perfiles se montan desde un bucket privado de Cloud Storage.',
    stack: [
      ['Interfaz', 'React · Vite'],
      ['API y streaming', 'FastAPI · Server-Sent Events'],
      ['Orquestación y contexto', 'LangGraph · historial acotado enviado por el navegador'],
      ['Modelos', 'OpenRouter · respuesta y clasificador configurables por separado'],
    ],
    contextTitle: 'Contexto y revisión',
    contextNote:
      'Las respuestas se apoyan en cv.md y docs/PROJECT.md. El borrador se revisa antes de mostrarse; el grafo puede reintentarlo una vez o recurrir a una respuesta alternativa.',
    memoryTitle: 'Contexto de conversación',
    memoryNote: 'El navegador conserva el contexto de esta pestaña y lo envía en cada pregunta; cada turno del servidor es independiente.',
    observabilityTitle: 'Observabilidad opcional',
    observabilityNote: 'El proyecto puede enviar trazas a Langfuse y OpenTelemetry cuando están configurados; no es una señal en vivo de esta pantalla.',
    moreInfo: 'Más información sobre Adrián y el asistente',
    contact: 'Contacto',
    projectLink: 'GitHub',
    footerNote: 'Perfil profesional basado en el CV de Adrián.',
    profileLoading: 'Preparando esta versión del portfolio…',
    profileNotFound: 'No encontramos este perfil personalizado.',
    profileLoadError: 'No se pudo cargar este perfil. Comprueba tu conexión e inténtalo de nuevo.',
    backToPortfolio: 'Ir al portfolio general',
  },
  en: {
    languageLabel: 'Language',
    focus: 'AI Engineer',
    location: 'Madrid',
    bannerAlt: 'Panoramic painted landscape of a path between fields and trees.',
    linkedIn: 'LinkedIn',
    introduction: 'Software engineer with 3+ years of experience across LLM integration, data pipelines, and distributed backend systems.',
    experience: 'Experience',
    trcRole:
      'Spring Boot backend services and asynchronous workflows in distributed systems.',
    role41ops:
      'MCP servers for enterprise LLM workflows, Java and Spring Boot microservices, and data processing with Spark.',
    siCongresosRole:
      'Spring Boot backend services, web applications, and system maintenance and migration.',
    skills: 'Areas of work',
    backend: 'Backend',
    dataEngineering: 'Data',
    aiEngineering: 'Applied AI',
    development: 'Professional development',
    courseTitle: 'AI Agents Course — Hugging Face',
    courseCompletion: 'Completed 2026',
    courseDescription:
      'Foundations of LLMs, tools and function calling; the reasoning–action–observation loop; smolagents, LlamaIndex and LangGraph; Agentic RAG, and agent monitoring and evaluation.',
    profileTitle: 'Experience',
    profileNote: 'CV and tools',
    openDetails: 'Explore',
    closeDetails: 'Close',
    flowTitle: 'How it works',
    assistantNote: 'A look inside the system behind the chat.',
    flowDisclaimer: 'A static overview of the implemented flow; it does not show live activity.',
    stages: [
      ['Question → API', 'React and Vite send your question to FastAPI.'],
      ['Input review', 'A classifier reviews the message before answering.'],
      ['Contextual answer', 'LangGraph uses the CV and project notes to prepare the answer.'],
      ['Review → chat', 'Only an approved answer is streamed to the chat over SSE.'],
    ],
    stackTitle: 'Technologies',
    deploymentTitle: 'Deployment',
    deploymentNote:
      'Vercel serves the React/Vite frontend and proxies /api/* to FastAPI on Cloud Run. Cloud Run can scale to zero; the CV and profiles are mounted from a private Cloud Storage bucket.',
    stack: [
      ['Interface', 'React · Vite'],
      ['API and streaming', 'FastAPI · Server-Sent Events'],
      ['Orchestration and context', 'LangGraph · bounded history sent by the browser'],
      ['Models', 'OpenRouter · separately configurable answer and classifier models'],
    ],
    contextTitle: 'Context and review',
    contextNote:
      'Answers are grounded in cv.md and docs/PROJECT.md. The draft is reviewed before it appears; the graph can retry once or fall back to an alternative response.',
    memoryTitle: 'Conversation context',
    memoryNote: 'The browser keeps this tab’s conversation context and sends it with each question; each server turn is independent.',
    observabilityTitle: 'Optional observability',
    observabilityNote: 'The project can send traces to Langfuse and OpenTelemetry when configured; this is not a live signal on this screen.',
    moreInfo: 'More about Adrián and the assistant',
    contact: 'Contact',
    projectLink: 'GitHub',
    footerNote: "Professional profile based on Adrián's CV.",
    profileLoading: 'Preparing this portfolio…',
    profileNotFound: 'This personalized profile could not be found.',
    profileLoadError: 'This profile could not be loaded. Check your connection and try again.',
    backToPortfolio: 'Go to the main portfolio',
  },
}

const EXPERIENCE = {
  es: [
    {
      company: 'TRC',
      title: 'Ingeniero de software',
      place: 'España',
      dates: 'Mayo 2026 — Actualidad',
      descriptionKey: 'trcRole',
    },
    {
      company: '41OPS',
      title: 'Ingeniero de software',
      place: 'Madrid',
      dates: 'Septiembre 2024 — Mayo 2026',
      descriptionKey: 'role41ops',
    },
    {
      company: 'SiCongresos',
      title: 'Ingeniero de software',
      place: 'Granada',
      dates: 'Mayo 2023 — Mayo 2024',
      descriptionKey: 'siCongresosRole',
    },
  ],
  en: [
    {
      company: 'TRC',
      title: 'Software engineer',
      place: 'Spain',
      dates: 'May 2026 — Present',
      descriptionKey: 'trcRole',
    },
    {
      company: '41OPS',
      title: 'Software engineer',
      place: 'Madrid',
      dates: 'September 2024 — May 2026',
      descriptionKey: 'role41ops',
    },
    {
      company: 'SiCongresos',
      title: 'Software engineer',
      place: 'Granada',
      dates: 'May 2023 — May 2024',
      descriptionKey: 'siCongresosRole',
    },
  ],
}

function getInitialLanguage() {
  if (typeof navigator === 'undefined') return 'en'
  return navigator.language.toLowerCase().startsWith('es') ? 'es' : 'en'
}

function getProfileIdFromPath() {
  const path = window.location.pathname.replace(/\/$/, '') || '/'
  if (path === '/' || path === '/index.html') return 'general'
  return path.match(/^\/p\/([a-z0-9-]+)$/)?.[1] ?? null
}

export default function App() {
  const [language, setLanguage] = useState(getInitialLanguage)
  const copy = COPY[language]
  const profileId = getProfileIdFromPath()
  const [profileState, setProfileState] = useState(() =>
    profileId === 'general'
      ? { status: 'ready', profile: null }
      : profileId
        ? { status: 'loading', profile: null }
        : { status: 'not-found', profile: null },
  )

  useEffect(() => {
    if (!profileId || profileId === 'general') return undefined

    const controller = new AbortController()
    fetch(`/api/profiles/${encodeURIComponent(profileId)}`, { signal: controller.signal })
      .then((response) => {
        if (!response.ok) {
          const error = new Error('Profile request failed')
          error.status = response.status
          throw error
        }
        return response.json()
      })
      .then((profile) => setProfileState({ status: 'ready', profile }))
      .catch((error) => {
        if (controller.signal.aborted) return
        setProfileState({
          status: error.status === 404 ? 'not-found' : 'error',
          profile: null,
        })
      })

    return () => controller.abort()
  }, [profileId])

  useEffect(() => {
    if (profileId !== 'general') return undefined
    fetch('/api/warmup', { cache: 'no-store', keepalive: true }).catch(() => {})
    return undefined
  }, [profileId])

  useEffect(() => {
    document.documentElement.lang = language
    document.title =
      language === 'es'
      ? 'Adrián Amaro — Portfolio AI Engineer'
        : 'Adrián Amaro — AI Engineer portfolio'
  }, [language])

  if (profileState.status !== 'ready') {
    const message =
      profileState.status === 'loading'
        ? copy.profileLoading
        : profileState.status === 'not-found'
          ? copy.profileNotFound
          : copy.profileLoadError

    return (
      <div className="studio-app">
        <main className="studio-main">
          <section className="studio-profile-status" aria-live="polite">
            <p>{message}</p>
            {profileState.status !== 'loading' && (
              <a href="/">{copy.backToPortfolio}</a>
            )}
          </section>
        </main>
      </div>
    )
  }

  return (
    <div className="studio-app">
      <header className="studio-header">
        <a className="studio-brand" href="#inicio" aria-label="Adrián Amaro">
          <span className="studio-brand-copy">
            <strong>Adrián Amaro</strong>
            <span>{copy.focus} <i aria-hidden="true">·</i> {copy.location}</span>
          </span>
        </a>

        <div className="studio-language" role="group" aria-label={copy.languageLabel}>
          <button
            type="button"
            aria-pressed={language === 'es'}
            onClick={() => setLanguage('es')}
          >
            ES
          </button>
          <span aria-hidden="true">/</span>
          <button
            type="button"
            aria-pressed={language === 'en'}
            onClick={() => setLanguage('en')}
          >
            EN
          </button>
        </div>
      </header>

      <main className="studio-main" id="inicio">
        <Chat language={language} profile={profileState.profile} profileId={profileId} />

        <section className="studio-details" aria-label={copy.moreInfo}>
          <details className="studio-details-item">
            <summary>
              <span>{copy.profileTitle}</span>
              <span className="studio-details-note">{copy.profileNote}</span>
              <span
                className="studio-details-action"
                data-closed-label={copy.openDetails}
                data-open-label={copy.closeDetails}
                aria-hidden="true"
              >
                <svg viewBox="0 0 20 20" fill="none" aria-hidden="true">
                  <path d="m5 7.5 5 5 5-5" />
                </svg>
              </span>
            </summary>
            <div className="studio-profile-content">
              <figure className="studio-profile-cover">
                <img
                  src="/images/adrian-amaro-banner.webp"
                  alt={copy.bannerAlt}
                  loading="lazy"
                  decoding="async"
                />
              </figure>
              <p className="studio-profile-intro">{copy.introduction}</p>
              <div className="studio-experience-list">
                {EXPERIENCE[language].map((entry) => (
                  <article className="studio-experience" key={entry.company}>
                    <p className="studio-experience-date">{entry.dates}</p>
                    <div>
                      <h3>{entry.company}</h3>
                      <p className="studio-experience-meta">
                        {entry.title} <span aria-hidden="true">·</span> {entry.place}
                      </p>
                      <p className="studio-experience-description">{copy[entry.descriptionKey]}</p>
                      {entry.detail && <p className="studio-experience-detail">{entry.detail}</p>}
                    </div>
                  </article>
                ))}
              </div>
              <section className="studio-development" aria-labelledby="development-title">
                <h3 id="development-title">{copy.development}</h3>
                <p className="studio-development-course">
                  <strong>{copy.courseTitle}</strong>
                  <span>{copy.courseCompletion}</span>
                </p>
                <p className="studio-development-description">{copy.courseDescription}</p>
              </section>
              <div className="studio-skills">
                <h3>{copy.skills}</h3>
                <p><strong>{copy.backend}</strong> Java · Spring Boot · Python</p>
                <p><strong>{copy.dataEngineering}</strong> Spark · SQL · Hive · Airflow</p>
                <p><strong>{copy.aiEngineering}</strong> LangChain · OpenAI APIs · Hugging Face · LLaMA · MCP</p>
              </div>
            </div>
          </details>

          <details className="studio-details-item studio-flow-details">
            <summary>
              <span>{copy.flowTitle}</span>
              <span className="studio-details-note">{copy.assistantNote}</span>
              <span
                className="studio-details-action"
                data-closed-label={copy.openDetails}
                data-open-label={copy.closeDetails}
                aria-hidden="true"
              >
                <svg viewBox="0 0 20 20" fill="none" aria-hidden="true">
                  <path d="m5 7.5 5 5 5-5" />
                </svg>
              </span>
            </summary>
            <div className="studio-flow-content">
              <ol className="studio-process">
                {copy.stages.map(([title, description], index) => (
                  <li key={title}>
                    <span className="studio-process-index" aria-hidden="true">{index + 1}</span>
                    <div>
                      <h3>{title}</h3>
                      <p>{description}</p>
                    </div>
                  </li>
                ))}
              </ol>
              <p className="studio-flow-disclaimer">{copy.flowDisclaimer}</p>
              <div className="studio-tech-grid">
                <section>
                  <h3>{copy.stackTitle}</h3>
                  <dl>
                    {copy.stack.map(([label, value]) => (
                      <div key={label}>
                        <dt>{label}</dt>
                        <dd>{value}</dd>
                      </div>
                    ))}
                  </dl>
                </section>
                <section>
                  <h3>{copy.deploymentTitle}</h3>
                  <p>{copy.deploymentNote}</p>
                </section>
                <section>
                  <h3>{copy.contextTitle}</h3>
                  <p>{copy.contextNote}</p>
                </section>
                <section>
                  <h3>{copy.memoryTitle}</h3>
                  <p>{copy.memoryNote}</p>
                </section>
              </div>
              <p className="studio-observability">
                <strong>{copy.observabilityTitle}</strong> {copy.observabilityNote}
              </p>
            </div>
          </details>
        </section>
      </main>

      <footer className="studio-footer">
        <span>{copy.footerNote}</span>
        <nav aria-label={copy.contact}>
          <a href="mailto:adrianamaroquero@gmail.com">{copy.contact}</a>
          <a href="https://www.linkedin.com/in/adrian-amaro/" target="_blank" rel="noreferrer">
            {copy.linkedIn}
          </a>
          <a href="https://github.com/aaamaroq/ecommerce" target="_blank" rel="noreferrer">
            {copy.projectLink}
          </a>
        </nav>
      </footer>
    </div>
  )
}
