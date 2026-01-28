// app/page.tsx
export default function Home() {
  return (
    <main className="h-screen flex items-center justify-center">
      <div className="text-center space-y-6">
        <h1 className="text-4xl font-bold">
          🔐 Send photos that unlock when paid
        </h1>
        <p className="text-gray-600">
          Share private images securely and get paid first.
        </p>
        <a href="/upload" className="px-6 py-3 bg-black text-white rounded">
          Get Started
        </a>
      </div>
    </main>
  )
}
