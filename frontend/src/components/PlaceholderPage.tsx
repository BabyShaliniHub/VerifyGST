type Props = {
  title: string
  description: string
}

export default function PlaceholderPage({ title, description }: Props) {
  return (
    <section>
      <h1 className="text-2xl font-semibold">{title}</h1>
      <p className="mt-2 max-w-2xl">{description}</p>
      <p className="mt-6 max-w-2xl border-l-4 border-gold bg-surface px-4 py-3">
        Not built yet. This page is a placeholder and shows no real data.
      </p>
    </section>
  )
}
