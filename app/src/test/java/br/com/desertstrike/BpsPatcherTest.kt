package br.com.desertstrike

import org.junit.Test
import br.com.desertstrike.BpsPatcher
import br.com.desertstrike.ModPatcher
import java.io.ByteArrayOutputStream
import java.util.zip.CRC32

private fun enc(value: Long): ByteArray {
    var remaining = value
    val out = ByteArrayOutputStream()
    while (true) {
        val x = (remaining and 127).toInt()
        remaining = remaining ushr 7
        if (remaining == 0L) { out.write(x or 128); return out.toByteArray() }
        out.write(x)
        remaining--
    }
}
private fun addCrc(out: ByteArrayOutputStream, data: ByteArray) {
    val checksum = CRC32().apply { update(data) }.value
    repeat(4) { out.write(((checksum ushr (8 * it)) and 255).toInt()) }
}
private fun makePatch(source: ByteArray, target: ByteArray, commands: ByteArray): ByteArray {
    val out = ByteArrayOutputStream()
    out.write("BPS1".toByteArray())
    out.write(enc(source.size.toLong()))
    out.write(enc(target.size.toLong()))
    out.write(enc(0))
    out.write(commands)
    addCrc(out, source)
    addCrc(out, target)
    addCrc(out, out.toByteArray())
    return out.toByteArray()
}
class BpsPatcherTest {
    @Test fun applyAndRejectInvalidInput() {
    val source = "ABCDEF".toByteArray()
    val expected = "ABXYDEFXYXY".toByteArray()
    val commands = ByteArrayOutputStream().apply {
        write(enc(4))
        write(enc(5)); write("XY".toByteArray())
        write(enc(10)); write(enc(6))
        write(enc(7)); write(enc(4))
        write(enc(7)); write(enc(6))
    }.toByteArray()
    val patch = makePatch(source, expected, commands)
    check(BpsPatcher.apply(source, patch).contentEquals(expected))
    check(ModPatcher.apply(source, patch).contentEquals(expected))
    check(source.contentEquals("ABCDEF".toByteArray()))
    check(ModPatcher.supported("EXAMPLE.BPS") && ModPatcher.supported("example.ips"))
    check(!ModPatcher.supported("evil.exe"))
    fun mustFail(bytes: ByteArray, rom: ByteArray = source) {
        var failed = false
        try { BpsPatcher.apply(rom, bytes) } catch (e: IllegalArgumentException) { failed = true }
        check(failed) { "Expected failure for invalid BPS" }
    }
    mustFail(patch, "abcDEF".toByteArray())
    mustFail(patch.copyOf().also { it[it.size - 1] = (it.last().toInt() xor 1).toByte() })
    mustFail(patch.copyOf(patch.size - 1))
    val bogus = makePatch(source, expected, byteArrayOf(0x80.toByte()))
    mustFail(bogus)
    println("BPS: OK (four commands, input CRC, patch CRC, truncated, bounds)")
}

}
