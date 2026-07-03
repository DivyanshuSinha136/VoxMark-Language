/* VoxMark WASM Loader — Author: Divyanshu Sinha */
async function loadVoxMarkWASM(wasmUrlOrBytes, targetElement) {
  let buffer;
  if (typeof wasmUrlOrBytes === 'string') {
    const resp = await fetch(wasmUrlOrBytes);
    buffer = await resp.arrayBuffer();
  } else {
    buffer = wasmUrlOrBytes.buffer || wasmUrlOrBytes;
  }
  const { instance } = await WebAssembly.instantiate(buffer, {});
  const exp     = instance.exports;
  const mem     = new Uint8Array(exp.memory.buffer);
  const count   = exp.widget_count();
  const decoder = new TextDecoder('utf-8');
  const parts   = [];
  for (let i = 0; i < count; i++) {
    const ptr = exp.get_widget_ptr(i);
    const len = exp.get_widget_len(i);
    parts.push(decoder.decode(mem.slice(ptr, ptr + len)));
  }
  const html = parts.join('');
  if (targetElement) {
    targetElement.innerHTML = html;
    targetElement.dispatchEvent(new CustomEvent('voxmark:wasm:ready', {
      detail: { widgetCount: count, totalBytes: exp.render_all() }
    }));
  }
  return { html, count, totalBytes: exp.render_all(), instance };
}
