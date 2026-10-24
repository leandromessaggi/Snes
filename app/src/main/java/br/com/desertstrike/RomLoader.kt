package br.com.desertstrike

import android.content.Context
import android.net.Uri
import java.io.ByteArrayOutputStream
import java.util.zip.ZipInputStream

object RomLoader {
    private const val MAX_ROM = 12 * 1024 * 1024
    fun read(context: Context, uri: Uri): ByteArray {
        val raw = context.contentResolver.openInputStream(uri)?.use { readCapped(it, MAX_ROM + 65536) }
            ?: error("Arquivo não encontrado")
        val file = if (raw.size >= 4 && raw[0] == 0x50.toByte() && raw[1] == 0x4b.toByte()) {
            ZipInputStream(raw.inputStream()).use { zip ->
                var chosen: ByteArray? = null
                while (true) {
                    val entry = zip.nextEntry ?: break
                    if (!entry.isDirectory && (entry.name.endsWith(".smc", true) || entry.name.endsWith(".sfc", true))) {
                        chosen = readCapped(zip, MAX_ROM + 512)
                        break
                    }
                }
                chosen ?: error("ZIP não contém ROM .smc/.sfc")
            }
        } else raw
        val unheadered = if (file.size % 1024 == 512) file.copyOfRange(512, file.size) else file
        require(unheadered.size in (256 * 1024)..MAX_ROM && unheadered.size % 1024 == 0) { "ROM SNES inválida" }
        return unheadered
    }
    fun readCapped(stream: java.io.InputStream, max: Int): ByteArray {
        val out = ByteArrayOutputStream()
        val buff = ByteArray(8192)
        while (true) {
            val n = stream.read(buff)
            if (n < 0) break
            if (n == 0) continue
            require(out.size() + n <= max) { "Arquivo grande demais" }
            out.write(buff, 0, n)
        }
        return out.toByteArray()
    }
}
