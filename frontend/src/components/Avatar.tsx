import type { Face } from '../types'

type Props = { kind: 'human' | 'avatar'; face: Face; size?: number }

/** Volto illustrato: bordo pieno per le persone umane, tratteggiato per gli avatar. */
export function Avatar({ kind, face, size = 44 }: Props) {
  const human = kind === 'human'
  const hair = face.hair ?? '#3A3E47'
  return (
    <svg width={size} height={size} viewBox="0 0 44 44" aria-hidden="true" style={{ flex: '0 0 auto' }}>
      <circle cx="22" cy="22" r="20.5" fill={human ? '#EEF0FB' : '#E3F4EF'} stroke={human ? '#2A3AA8' : '#0B6B53'}
        strokeWidth={1.5} strokeDasharray={human ? undefined : '3 2.5'} />
      {face.longHair && <path d="M12.5 19 Q11 31 15 34 L16 21 Z M31.5 19 Q33 31 29 34 L28 21 Z" fill={hair} />}
      <path d="M10 41 Q22 28 34 41 Z" fill={face.shirt ?? '#5A5F6A'} />
      <circle cx="22" cy="20" r="9.5" fill={face.skin ?? '#E2B58F'} />
      <path d="M12.5 19 Q13 9 22 9 Q31 9 31.5 19 Q28 13.5 22 13.5 Q16 13.5 12.5 19 Z" fill={hair} />
      <circle cx="18.6" cy="21" r="1.15" fill="#1B1E23" />
      <circle cx="25.4" cy="21" r="1.15" fill="#1B1E23" />
      <path d="M19.2 24.6 Q22 26.8 24.8 24.6" fill="none" stroke="#1B1E23" strokeWidth={1.2} strokeLinecap="round" />
    </svg>
  )
}

export function TypeTag({ kind }: { kind: 'human' | 'avatar' }) {
  return <span className={kind === 'human' ? 'tag tag-human' : 'tag tag-avatar'}>{kind === 'human' ? 'Umano' : 'Avatar'}</span>
}
