// app/upload/page.tsx
'use client'

import { useState } from 'react'
import { supabase } from '@/lib/supabase'

export default function Upload() {
  const [file, setFile] = useState<File | null>(null)
  const [price, setPrice] = useState(25)

  async function handleUpload() {
    if (!file) return

    const path = `${Date.now()}-${file.name}`

    await supabase.storage
      .from('media')
      .upload(path, file)

    const { data } = await supabase
      .from('locked_media')
      .insert({ image_path: path, price })
      .select()
      .single()

    window.location.href = `/unlock/${data.id}`
  }

  return (
    <div className="p-8 max-w-md mx-auto space-y-4">
      <input type="file" onChange={e => setFile(e.target.files?.[0] || null)} />
      <input
        type="number"
        value={price}
        onChange={e => setPrice(+e.target.value)}
        className="border p-2 w-full"
      />
      <button onClick={handleUpload} className="bg-black text-white px-4 py-2">
        Create Locked Link
      </button>
    </div>
  )
}
