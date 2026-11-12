// AudioWorklet della dettatura: raccoglie l'audio del microfono in blocchi
// di 4096 campioni e li passa alla pagina, che li da' al riconoscitore
// (app/voice.js). Sostituisce ScriptProcessorNode, deprecato, che lavora
// nel thread della pagina.
class VoiceTap extends AudioWorkletProcessor {
  constructor() {
    super();
    this.block = new Float32Array(4096);
    this.filled = 0;
  }

  process(inputs) {
    const channel = inputs[0] && inputs[0][0];
    if (channel) {
      let i = 0;
      while (i < channel.length) {
        const n = Math.min(channel.length - i, this.block.length - this.filled);
        this.block.set(channel.subarray(i, i + n), this.filled);
        this.filled += n;
        i += n;
        if (this.filled === this.block.length) {
          this.port.postMessage(this.block.slice());
          this.filled = 0;
        }
      }
    }
    return true;
  }
}

registerProcessor("voice-tap", VoiceTap);
