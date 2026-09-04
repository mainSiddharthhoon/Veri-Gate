/**
 * ============================================================================
 * Development Guard: Live Server WebSocket Interceptor
 * ============================================================================
 * When the backend processes images (e.g. cropping the face or running ELA),
 * it writes temporary files to the disk. VS Code Live Server detects these
 * changes and sends a WebSocket 'reload' message mid-screening.
 * This interceptor drops the reload message so active screenings complete.
 */

if ('WebSocket' in window) {
  const OriginalWebSocket = window.WebSocket;
  window.WebSocket = function(url, protocols) {
    const ws = new OriginalWebSocket(url, protocols);
    let onmessageHandler = null;
    Object.defineProperty(ws, 'onmessage', {
      get() { return onmessageHandler; },
      set(handler) {
        onmessageHandler = function(msg) {
          if (typeof msg.data === 'string' && msg.data.includes('reload')) {
            console.warn('Blocked Live Server from reloading the page mid-screening.');
            return; // Drop reload message
          }
          if (handler) return handler.call(ws, msg);
        };
      }
    });
    return ws;
  };
  window.WebSocket.prototype = OriginalWebSocket.prototype;
}
