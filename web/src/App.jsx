import Chat from './components/Chat.jsx'

export default function App() {
  return (
    <div className="flex h-full flex-col bg-slate-950 text-slate-100">
      <header className="border-b border-slate-800 px-6 py-4">
        <div className="mx-auto flex max-w-3xl items-baseline justify-between">
          <div>
            <h1 className="text-lg font-semibold tracking-tight">Adrián Amaro</h1>
            <p className="text-sm text-slate-400">
              Software Engineer — AI Portfolio
            </p>
          </div>
          <span className="hidden text-xs text-slate-500 sm:block">
            Ask me about my experience
          </span>
        </div>
      </header>

      <main className="flex-1 overflow-hidden">
        <Chat />
      </main>
    </div>
  )
}
