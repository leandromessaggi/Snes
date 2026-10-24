package br.com.desertstrike

import java.util.zip.CRC32

/** BPS1 patch: bounded size, all four command types, and three mandatory CRC32 checks. */
object BpsPatcher {
    private const val LIMIT = 16 * 1024 * 1024

    fun apply(source: ByteArray, patch: ByteArray): ByteArray {
        require(patch.size >= 19 && patch.copyOfRange(0, 4).contentEquals("BPS1".toByteArray(Charsets.US_ASCII))) {
            "Patch BPS inválido"
        }
        val footer = patch.size - 12
        var cursor = 4

        fun readByte(): Int {
            require(cursor < footer) { "Patch BPS truncado" }
            return patch[cursor++].toInt() and 255
        }
        fun readVar(): Long {
            var result = 0L
            var multiplier = 1L
            while (true) {
                val value = readByte()
                val digit = (value and 0x7f).toLong()
                require(digit == 0L || multiplier <= Long.MAX_VALUE / digit) { "Inteiro BPS grande demais" }
                val term = digit * multiplier
                require(result <= Long.MAX_VALUE - term) { "Inteiro BPS fora dos limites" }
                result += term
                if (value and 0x80 != 0) return result
                require(multiplier <= (Long.MAX_VALUE shr 8)) { "Inteiro BPS grande demais" }
                multiplier = multiplier shl 7
                require(result <= Long.MAX_VALUE - multiplier) { "Inteiro BPS fora dos limites" }
                result += multiplier
            }
        }
        fun readSigned(): Long {
            val value = readVar()
            val magnitude = value ushr 1
            return if (value and 1L != 0L) -magnitude else magnitude
        }
        fun footerCrc(at: Int): Long =
            ((patch[at].toLong() and 255L) or
                ((patch[at + 1].toLong() and 255L) shl 8) or
                ((patch[at + 2].toLong() and 255L) shl 16) or
                ((patch[at + 3].toLong() and 255L) shl 24))
        fun crc(data: ByteArray, size: Int = data.size): Long =
            CRC32().apply { update(data, 0, size) }.value

        val sourceLength = readVar()
        val targetLength = readVar()
        val metadataLength = readVar()
        require(sourceLength == source.size.toLong()) { "BPS requer ROM de tamanho diferente" }
        require(targetLength in 1..LIMIT.toLong()) { "BPS ultrapassa limite de 16 MiB" }
        require(metadataLength <= (footer - cursor).toLong()) { "Metadados BPS truncados" }
        cursor += metadataLength.toInt()
        require(crc(source) == footerCrc(footer)) { "CRC da ROM original não corresponde ao BPS" }
        require(crc(patch, patch.size - 4) == footerCrc(footer + 8)) { "CRC do patch BPS inválido" }

        val target = ByteArray(targetLength.toInt())
        var output = 0
        var sourceRelative = 0L
        var targetRelative = 0L
        while (output < target.size) {
            val command = readVar()
            val length = (command ushr 2) + 1
            require(length in 1..(target.size - output).toLong()) { "Operação BPS fora do destino" }
            val n = length.toInt()
            when ((command and 3L).toInt()) {
                0 -> {
                    require(output.toLong() + n <= source.size) { "Leitura da origem fora do limite" }
                    source.copyInto(target, output, output, output + n)
                }
                1 -> {
                    require(n <= footer - cursor) { "Dados literais BPS truncados" }
                    patch.copyInto(target, output, cursor, cursor + n)
                    cursor += n
                }
                2 -> {
                    val delta = readSigned()
                    require((delta >= 0 || sourceRelative >= -delta) &&
                        (delta <= 0 || sourceRelative <= Long.MAX_VALUE - delta)) { "Offset BPS inválido" }
                    sourceRelative += delta
                    require(sourceRelative >= 0 && sourceRelative <= source.size.toLong() - n) {
                        "Cópia BPS fora da ROM"
                    }
                    source.copyInto(target, output, sourceRelative.toInt(), sourceRelative.toInt() + n)
                    sourceRelative += n
                }
                3 -> {
                    val delta = readSigned()
                    require((delta >= 0 || targetRelative >= -delta) &&
                        (delta <= 0 || targetRelative <= Long.MAX_VALUE - delta)) { "Offset BPS inválido" }
                    targetRelative += delta
                    require(targetRelative >= 0 && targetRelative < output) { "Cópia BPS antes dos dados gravados" }
                    for (i in 0 until n) {
                        require(targetRelative < output + i) { "Referência BPS inválida" }
                        target[output + i] = target[targetRelative.toInt()]
                        targetRelative++
                    }
                }
            }
            output += n
        }
        require(cursor == footer) { "Dados extras no patch BPS" }
        require(crc(target) == footerCrc(footer + 4)) { "CRC do resultado BPS inválido" }
        return target
    }
}
