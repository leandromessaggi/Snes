package br.com.desertstrike

object NativeCore {
    init { System.loadLibrary("desert_bridge") }
    external fun start(corePath: String, storagePath: String, rom: ByteArray): Double
    external fun lastError(): String
    external fun stats(): String
    external fun fps(): Double
    external fun stop()
    external fun frame(pixels: IntArray): Int
    external fun input(bits: Int)
    external fun drainAudio(target: ShortArray): Int
    external fun saveState(): ByteArray?
    external fun loadState(state: ByteArray): Boolean
    external fun saveRam(): ByteArray?
    external fun loadRam(data: ByteArray): Boolean
    external fun traceStart(): Boolean
    external fun traceStop(): String?
}
