import { useEffect, useRef } from 'react'

const rand = (a, b) => a + Math.random() * (b - a)

// A meteor shower: every meteor shares one radiant direction (picked per page load) with a few
// degrees of jitter, like a real shower. A faint static star field sits behind it.
export default function Stars() {
  const ref = useRef(null)

  useEffect(() => {
    const canvas = ref.current
    const ctx = canvas.getContext('2d')
    const reduced = matchMedia('(prefers-reduced-motion: reduce)')
    const dark = matchMedia('(prefers-color-scheme: dark)')
    const heading = rand(200, 240) * (Math.PI / 180) // travel direction: down and to the left
    let w = 0, h = 0, field = [], meteors = [], color = '', strength = 1, frame = 0, timer = 0

    const readColor = () => {
      const css = getComputedStyle(document.documentElement)
      color = css.getPropertyValue('--star').trim()
      strength = parseFloat(css.getPropertyValue('--star-strength')) || 1
    }

    const resize = () => {
      const dpr = Math.min(devicePixelRatio || 1, 2)
      w = innerWidth
      h = innerHeight
      canvas.width = w * dpr
      canvas.height = h * dpr
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0)
      field = Array.from({ length: Math.round((w * h) / 9000) }, () => ({
        x: Math.random() * w, y: Math.random() * h, r: rand(0.4, 1.1), a: rand(0.15, 0.55),
      }))
      draw(performance.now())
    }

    const spawn = () => {
      const angle = heading + rand(-0.07, 0.07)
      meteors.push({
        // Start anywhere along an extended top/right band so the streak crosses the viewport.
        x: rand(w * 0.1, w * 1.2), y: rand(-h * 0.1, h * 0.55),
        dx: Math.cos(angle), dy: -Math.sin(angle),
        len: rand(90, 180), dist: rand(260, 520), dur: rand(650, 1150), born: performance.now(),
      })
      if (!frame) frame = requestAnimationFrame(draw)
    }

    const schedule = () => {
      timer = setTimeout(() => {
        if (!document.hidden && !reduced.matches) {
          spawn()
          if (Math.random() < 0.15) setTimeout(spawn, rand(120, 300))
        }
        schedule()
      }, rand(1200, 4500))
    }

    function draw(now) {
      ctx.clearRect(0, 0, w, h)
      for (const s of field) {
        ctx.fillStyle = `rgb(${color} / ${s.a * strength})`
        ctx.beginPath()
        ctx.arc(s.x, s.y, s.r, 0, Math.PI * 2)
        ctx.fill()
      }
      meteors = meteors.filter((m) => now - m.born < m.dur)
      for (const m of meteors) {
        const t = (now - m.born) / m.dur
        const hx = m.x + m.dx * m.dist * t, hy = m.y + m.dy * m.dist * t
        const tail = m.len * Math.min(1, t * 3)
        const tx = hx - m.dx * tail, ty = hy - m.dy * tail
        const alpha = t < 0.15 ? t / 0.15 : t > 0.7 ? (1 - t) / 0.3 : 1
        const grad = ctx.createLinearGradient(tx, ty, hx, hy)
        grad.addColorStop(0, `rgb(${color} / 0)`)
        grad.addColorStop(1, `rgb(${color} / ${0.85 * alpha * strength})`)
        ctx.strokeStyle = grad
        ctx.lineWidth = 1.3
        ctx.lineCap = 'round'
        ctx.beginPath()
        ctx.moveTo(tx, ty)
        ctx.lineTo(hx, hy)
        ctx.stroke()
      }
      frame = meteors.length ? requestAnimationFrame(draw) : 0
    }

    const onScheme = () => { readColor(); draw(performance.now()) }
    readColor()
    resize()
    schedule()
    addEventListener('resize', resize)
    dark.addEventListener('change', onScheme)
    return () => {
      clearTimeout(timer)
      cancelAnimationFrame(frame)
      removeEventListener('resize', resize)
      dark.removeEventListener('change', onScheme)
    }
  }, [])

  return <canvas ref={ref} className="stars" aria-hidden="true" />
}
