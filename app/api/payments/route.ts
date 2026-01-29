import { NextResponse } from 'next/server'
import Stripe from 'stripe'

const stripe = new Stripe(process.env.STRIPE_SECRET_KEY!, {
  apiVersion: '2023-10-16'
})

export async function POST(req: Request) {
  try {
    const { mediaId, price, buyerEmail } = await req.json()

    if (!mediaId || !price || !buyerEmail) {
      return NextResponse.json({ error: 'Missing data' }, { status: 400 })
    }

    // 1️⃣ Create Stripe Checkout Session
    const session = await stripe.checkout.sessions.create({
      payment_method_types: ['card'],
      customer_email: buyerEmail,
      line_items: [
        {
          price_data: {
            currency: 'zar',
            product_data: {
              name: 'Locked Image Unlock'
            },
            unit_amount: price * 100
          },
          quantity: 1
        }
      ],
      mode: 'payment',

      success_url: `${process.env.NEXT_PUBLIC_SITE_URL}/unlock/${mediaId}?success=true`,
      cancel_url: `${process.env.NEXT_PUBLIC_SITE_URL}/unlock/${mediaId}?cancelled=true`,

      metadata: {
        mediaId,
        buyerEmail
      }
    })

    return NextResponse.json({
      checkoutUrl: session.url
    })
  } catch (err) {
    console.error(err)
    return NextResponse.json({ error: 'Payment error' }, { status: 500 })
  }
}
