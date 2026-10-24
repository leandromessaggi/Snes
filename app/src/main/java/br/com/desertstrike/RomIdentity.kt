package br.com.desertstrike

import java.security.MessageDigest

object RomIdentity {
    const val SUPPORTED_SHA256 = "606abf536440173ae36466db360c7db6b474beb7a105c8a62bc74a54cbe1c38b"
    private const val SUPPORTED_BYTES = 1024 * 1024
    fun digest(rom: ByteArray): String = MessageDigest.getInstance("SHA-256")
        .digest(rom).joinToString("") { "%02x".format(it) }
    fun valid(rom: ByteArray): Boolean = rom.size == SUPPORTED_BYTES && digest(rom) == SUPPORTED_SHA256
    fun check(rom: ByteArray) {
        require(valid(rom)) {
            "Esta versão experimental requer a ROM USA original analisada " +
                "(sem cabeçalho copier). SHA-256 diferente: ${digest(rom).take(12)}…"
        }
    }
}
