/**
 * @typedef {object} LinkClickEvent
 * @property {boolean} defaultPrevented
 * @property {number} button
 * @property {boolean} metaKey
 * @property {boolean} ctrlKey
 * @property {boolean} shiftKey
 * @property {boolean} altKey
 * @property {{ href: string }} currentTarget
 * @property {() => void} preventDefault
 */

/**
 * @param {{
 *   event: LinkClickEvent;
 *   isIosStandalone: boolean;
 *   openWindow: (url: string, target: string) => ({ opener: unknown } | null);
 *   assignLocation: (url: string) => void;
 * }} options
 */
export function handleIosStandaloneLinkClick({
  event,
  isIosStandalone,
  openWindow,
  assignLocation,
}) {
  if (
    event.defaultPrevented ||
    event.button !== 0 ||
    event.metaKey ||
    event.ctrlKey ||
    event.shiftKey ||
    event.altKey ||
    !isIosStandalone
  ) {
    return false;
  }

  event.preventDefault();
  const destination = event.currentTarget.href;
  let openedWindow = null;

  try {
    openedWindow = openWindow(destination, "_blank");
  } catch {
    // Use the normal navigation fallback below.
  }

  if (openedWindow === null) {
    assignLocation(destination);
    return true;
  }

  try {
    openedWindow.opener = null;
  } catch {
    // Cross-origin navigation can still continue when opener isolation fails.
  }

  return true;
}
