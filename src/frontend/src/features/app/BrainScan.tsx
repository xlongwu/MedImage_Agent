export function BrainScan() {
  return (
    <svg className="brain-scan" viewBox="0 0 760 420" role="img" aria-label="Synthetic MRI scan preview">
      <defs>
        <radialGradient id="brainFill" cx="48%" cy="43%" r="62%">
          <stop offset="0%" stopColor="#c7ced8" />
          <stop offset="50%" stopColor="#7d8796" />
          <stop offset="100%" stopColor="#151a22" />
        </radialGradient>
        <filter id="softGlow">
          <feGaussianBlur stdDeviation="1.5" />
        </filter>
      </defs>
      <rect width="760" height="420" fill="#05070b" />
      <path d="M196 289 C129 281 91 243 84 196 C76 138 113 86 177 70 C257 49 357 63 429 111 C498 157 517 229 482 286 C448 341 361 363 281 337 C251 327 227 298 196 289 Z" fill="url(#brainFill)" stroke="#e7edf8" strokeOpacity=".58" strokeWidth="4" />
      <path d="M152 220 C218 206 266 201 334 219 C383 232 425 259 465 295" fill="none" stroke="#06080d" strokeWidth="18" strokeLinecap="round" opacity=".72" />
      <path d="M168 142 C252 105 355 116 421 173" fill="none" stroke="#edf3fb" strokeWidth="7" opacity=".45" filter="url(#softGlow)" />
      <path d="M207 101 C227 145 222 190 187 235" fill="none" stroke="#121723" strokeWidth="11" opacity=".7" />
      <path d="M312 83 C282 146 287 208 343 259" fill="none" stroke="#e8eef7" strokeWidth="5" opacity=".36" />
      <path d="M411 132 C372 174 351 216 363 270" fill="none" stroke="#0a0d14" strokeWidth="12" opacity=".62" />
      <path d="M481 219 C541 224 584 251 614 298 C557 304 514 293 482 266" fill="#101620" stroke="#d6dfeb" strokeOpacity=".36" strokeWidth="3" />
      <path d="M623 300 C653 319 684 330 720 331" stroke="#eff4fb" strokeWidth="5" opacity=".35" />
      <g opacity=".28">
        {Array.from({ length: 9 }).map((_, index) => (
          <line key={index} x1={82 + index * 68} y1="32" x2={64 + index * 68} y2="392" stroke="#e8eef7" strokeWidth="1" />
        ))}
      </g>
    </svg>
  );
}
