package br.com.desertstrike

/** Restricts mod formats to data-only IPS and BPS files, no executable content. */
object ModPatcher {
    fun supported(filename: String): Boolean =
        filename.endsWith(".ips", true) || filename.endsWith(".bps", true)

    fun extension(patch: ByteArray): String = when {
        patch.size >= 5 && patch.copyOfRange(0, 5).contentEquals("PATCH".toByteArray(Charsets.US_ASCII)) -> "ips"
        patch.size >= 4 && patch.copyOfRange(0, 4).contentEquals("BPS1".toByteArray(Charsets.US_ASCII)) -> "bps"
        else -> throw IllegalArgumentException("Patch desconhecido (somente IPS/BPS)")
    }

    fun apply(source: ByteArray, patch: ByteArray): ByteArray = when (extension(patch)) {
        "ips" -> IpsPatcher.apply(source, patch)
        "bps" -> BpsPatcher.apply(source, patch)
        else -> error("Formato não suportado")
    }
}
