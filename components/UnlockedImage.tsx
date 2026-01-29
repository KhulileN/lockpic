import { supabase } from '@/lib/supabaseClient'
import Image from 'next/image'

type Props = {
  imagePath: string
}

export default async function UnlockedImage({ imagePath }: Props) {
  const { data } = await supabase.storage
    .from('media')
    .createSignedUrl(imagePath, 60)

  if (!data?.signedUrl) {
    return <p>Unable to load image</p>
  }

  return (
    <Image
      src={data.signedUrl}
      alt="Unlocked content"
      width={400}
      height={400}
      className="rounded-lg"
    />
  )
}
