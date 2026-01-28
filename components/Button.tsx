// components/Button.tsx
'use client'

interface ButtonProps {
  children: React.ReactNode
  onClick?: () => void
  className?: string
}

export default function Button({ children, onClick, className }: ButtonProps) {
  return (
    <button
      onClick={onClick}
      className={`bg-black text-white px-4 py-2 rounded hover:bg-gray-800 transition ${className}`}
    >
      {children}
    </button>
  )
}
