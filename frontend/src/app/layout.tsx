import type { Metadata } from 'next'
import './globals.css'

export const metadata: Metadata = {
  title: 'ROOT - Urban Tree Intelligence',
  description: 'Every threatened urban tree gets a living record, a compliance audit, and a public comment draft in 90 seconds.',
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="h-full">
      <body className="h-full antialiased" style={{ background: 'var(--paper)', color: 'var(--ink)', fontFamily: 'var(--font-body)' }}>
        {children}
      </body>
    </html>
  )
}
