const config = {
  pending: { label: 'Pendiente', classes: 'bg-yellow-100 text-yellow-800' },
  generating: { label: 'Generando', classes: 'bg-blue-100 text-blue-800' },
  completed: { label: 'Completado', classes: 'bg-green-100 text-green-800' },
  failed: { label: 'Error', classes: 'bg-red-100 text-red-800' },
}

export default function StatusBadge({ status }) {
  const { label, classes } = config[status] || config.pending

  return (
    <span
      className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold ${classes}`}
    >
      {status === 'generating' && (
        <span className="mr-1.5 h-2 w-2 rounded-full bg-blue-500 animate-pulse" />
      )}
      {label}
    </span>
  )
}
