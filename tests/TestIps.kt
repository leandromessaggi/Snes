import br.com.desertstrike.IpsPatcher

fun main() {
    val original = ByteArray(8) { it.toByte() }
    val ips = byteArrayOf(80,65,84,67,72, 0,0,2,0,2,0xab.toByte(),0xcd.toByte(),
        0,0,6,0,0,0,3,0x7f, 69,79,70)
    val after = IpsPatcher.apply(original, ips)
    check(after.contentEquals(byteArrayOf(0,1,0xab.toByte(),0xcd.toByte(),4,5,0x7f,0x7f,0x7f)))
    check(original.contentEquals(ByteArray(8){it.toByte()}))
    try {
        IpsPatcher.apply(original,byteArrayOf(1,2,3))
        error("Truncated patch should fail")
    } catch (_: IllegalArgumentException) {}
    println("IPS: OK")
}
