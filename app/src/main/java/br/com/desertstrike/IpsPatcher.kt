package br.com.desertstrike

/** Standard IPS: raw writes, RLE, EOF, optional final size; strict bounds, max 16 MiB. */
object IpsPatcher {
    private const val LIMIT = 16 * 1024 * 1024
    fun apply(source: ByteArray, patch: ByteArray): ByteArray {
        require(patch.size >= 8 && patch.copyOfRange(0, 5).contentEquals("PATCH".toByteArray(Charsets.US_ASCII))) { "Mod IPS inválido" }
        var result = source.copyOf()
        var pos = 5
        fun read16(): Int {
            require(pos + 2 <= patch.size) { "IPS truncado" }
            val v = ((patch[pos].toInt() and 255) shl 8) or (patch[pos + 1].toInt() and 255)
            pos += 2
            return v
        }
        fun expand(target: Int) {
            require(target in 0..LIMIT) { "Mod ultrapassa limite de 16 MiB" }
            if (target > result.size) result = result.copyOf(target)
        }
        var ended = false
        while (pos + 3 <= patch.size) {
            if (patch[pos] == 'E'.code.toByte() && patch[pos + 1] == 'O'.code.toByte() && patch[pos + 2] == 'F'.code.toByte()) {
                pos += 3
                ended = true
                break
            }
            val offset = ((patch[pos].toInt() and 255) shl 16) or ((patch[pos + 1].toInt() and 255) shl 8) or (patch[pos + 2].toInt() and 255)
            pos += 3
            val len = read16()
            if (len == 0) {
                val repeat = read16()
                require(pos < patch.size) { "IPS RLE truncado" }
                val value = patch[pos++]
                expand(offset + repeat)
                result.fill(value, offset, offset + repeat)
            } else {
                require(pos + len <= patch.size) { "IPS truncado" }
                expand(offset + len)
                patch.copyInto(result, offset, pos, pos + len)
                pos += len
            }
        }
        require(ended) { "IPS sem marca EOF" }
        if (pos + 3 == patch.size) {
            val size = ((patch[pos].toInt() and 255) shl 16) or ((patch[pos + 1].toInt() and 255) shl 8) or (patch[pos + 2].toInt() and 255)
            require(size <= LIMIT)
            result = result.copyOf(size)
        } else require(pos == patch.size) { "Dados extras no IPS" }
        return result
    }
}
