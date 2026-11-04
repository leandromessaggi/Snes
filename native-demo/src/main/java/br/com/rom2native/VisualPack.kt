package br.com.rom2native

import android.graphics.BitmapFactory
import org.json.JSONObject
import java.io.ByteArrayOutputStream
import java.security.MessageDigest
import java.util.zip.ZipInputStream

/**
 * Validates a data-only visual pack before handing ARGB pixels to the C++ renderer.
 * Never extracts arbitrary files or executes mod code.
 */
object VisualPack {
    data class Sprite(val pixels: IntArray, val width: Int, val height: Int)
    private const val MAX_PACK = 1024 * 1024
    private const val MAX_IMAGE = 512 * 1024
    private const val MAX_MANIFEST = 8192
    private const val FORMAT = "rom2native-visual-v1"

    private fun readLimited(zip: ZipInputStream, max: Int): ByteArray {
        val buffer = ByteArray(8192)
        val out = ByteArrayOutputStream()
        while (true) {
            val count = zip.read(buffer)
            if (count < 0) break
            if (count == 0) continue
            require(out.size().toLong() + count <= max) { "Arquivo do pacote muito grande" }
            out.write(buffer, 0, count)
        }
        return out.toByteArray()
    }

    private fun sha256(data: ByteArray): String =
        MessageDigest.getInstance("SHA-256").digest(data)
            .joinToString("") { "%02x".format(it) }

    fun parse(bytes: ByteArray, expectedRomHash: String): Sprite {
        require(bytes.size in 1..MAX_PACK) { "Pacote excede 1 MiB" }
        val entries = linkedMapOf<String, ByteArray>()
        ZipInputStream(bytes.inputStream()).use { zip ->
            while (true) {
                val entry = zip.nextEntry ?: break
                require(!entry.isDirectory) { "Diretórios não são aceitos no pacote visual" }
                val name = entry.name
                require(name == "manifest.json" || name == "helicopter.png") {
                    "Somente manifest.json e helicopter.png são permitidos"
                }
                require(!entries.containsKey(name)) { "Arquivo duplicado no pacote" }
                val max = if (name == "manifest.json") MAX_MANIFEST else MAX_IMAGE
                entries[name] = readLimited(zip, max)
                zip.closeEntry()
            }
        }
        require(entries.keys == setOf("manifest.json", "helicopter.png")) {
            "Manifesto ou imagem ausente"
        }
        val manifest = JSONObject(String(entries.getValue("manifest.json"), Charsets.UTF_8))
        require(manifest.optString("format") == FORMAT) { "Versão de pacote incompatível" }
        require(manifest.optString("rom_sha256") == expectedRomHash) {
            "Pacote destinado a outra revisão da ROM"
        }
        val asset = manifest.getJSONObject("asset")
        require(asset.optString("id") == "helicopter" &&
            asset.optString("file") == "helicopter.png") { "Asset inválido" }
        val png = entries.getValue("helicopter.png")
        require(sha256(png) == asset.optString("sha256")) { "SHA-256 do sprite não corresponde" }
        val signature = byteArrayOf(0x89.toByte(), 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a)
        require(png.size >= 33 && png.copyOfRange(0, 8).contentEquals(signature) &&
            (png[24].toInt() and 255) == 8 && (png[25].toInt() and 255) == 6) {
            "O sprite precisa ser PNG RGBA de 8 bits"
        }
        val bounds = BitmapFactory.Options().apply { inJustDecodeBounds = true }
        BitmapFactory.decodeByteArray(png, 0, png.size, bounds)
        val w = bounds.outWidth
        val h = bounds.outHeight
        require(w in 1..128 && h in 1..128 &&
            w == asset.getInt("width") && h == asset.getInt("height")) {
            "Dimensões do PNG incompatíveis com o manifesto"
        }
        val image = BitmapFactory.decodeByteArray(png, 0, png.size)
            ?: error("Não foi possível decodificar a imagem")
        try {
            require(image.width == w && image.height == h) { "Imagem inconsistente" }
            val pixels = IntArray(w * h)
            image.getPixels(pixels, 0, w, 0, 0, w, h)
            require(pixels.any { it ushr 24 != 0 }) { "Sprite totalmente transparente" }
            return Sprite(pixels, w, h)
        } finally {
            image.recycle()
        }
    }
}
