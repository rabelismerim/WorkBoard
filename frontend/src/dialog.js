export const dialogDirective = {
  mounted(element) {
    const previous = document.activeElement
    const focusable = () => [...element.querySelectorAll('button,input,textarea,select,a[href],[tabindex="0"]')].filter(el => !el.matches(':disabled') && el.getClientRects().length)
    const handler = event => {
      if (event.key !== 'Tab') return
      const items = focusable(), first = items[0], last = items.at(-1)
      if (!first) { event.preventDefault();return }
      if (event.shiftKey && (document.activeElement===first || !element.contains(document.activeElement))) { event.preventDefault();last.focus() }
      else if (!event.shiftKey && (document.activeElement===last || !element.contains(document.activeElement))) { event.preventDefault();first.focus() }
    }
    element.addEventListener('keydown',handler)
    element._dialogCleanup = () => {element.removeEventListener('keydown',handler); if(previous?.isConnected) previous.focus()}
    requestAnimationFrame(() => (element.querySelector('[autofocus]') || focusable().find(el=>el.matches('input,textarea,select')) || focusable()[0])?.focus())
  },
  unmounted(element) { element._dialogCleanup?.() },
}
