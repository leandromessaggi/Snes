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
    data class Sprite(val pixels: IntArray, val width: Int, val height: Int, val frames: Int)
    private const val MAX_PACK = 3 * 1024 * 1024
    private const val MAX_IMAGE = 2 * 1024 * 1024
    private const val MAX_MANIFEST = 8192
    private const val FORMAT = "rom2native-visual-v1"
    private const val FORMAT_8 = "rom2native-visual-v2"
    private val DIRECTIONS = arrayOf("N","NE","E","SE","S","SW","W","NW")

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
        require(bytes.size in 1..MAX_PACK) { "Pacote excede 3 MiB" }
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
        val format = manifest.optString("format")
        require(format == FORMAT || format == FORMAT_8) { "Versão de pacote incompatível" }
        val frames = if (format == FORMAT_8) 8 else 1
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
        require(w in 1..(128 * frames) && h in 1..128 && w % frames == 0 &&
            w / frames in 1..128 && w == asset.getInt("width") &&
            h == asset.getInt("height")) {
            "Dimensões do PNG incompatíveis com o manifesto"
        }
        if (frames == 8) {
            require(asset.optInt("frames") == 8 &&
                asset.optString("layout") == "horizontal" &&
                asset.optInt("frame_width") == w / 8 &&
                asset.optInt("frame_height") == h) { "Formato de atlas incompatível" }
            val dirs = asset.getJSONArray("directions")
            require(dirs.length() == DIRECTIONS.size &&
                DIRECTIONS.indices.all { i -> dirs.getString(i) == DIRECTIONS[i] }) {
                "Ordem das direções deve ser N,NE,E,SE,S,SW,W,NW"
            }
        } else {
            require(!asset.has("frames") || asset.getInt("frames") == 1) {
                "Pacote visual v1 só aceita um quadro"
            }
        }
        val image = BitmapFactory.decodeByteArray(png, 0, png.size)
            ?: error("Não foi possível decodificar a imagem")
        try {
            require(image.width == w && image.height == h) { "Imagem inconsistente" }
            val pixels = IntArray(w * h)
            image.getPixels(pixels, 0, w, 0, 0, w, h)
            val frameWidth = w / frames
            for (index in 0 until frames) {
                var hasOpaquePixel = false
                for (y in 0 until h) {
                    for (x in 0 until frameWidth) {
                        if (pixels[y * w + index * frameWidth + x] ushr 24 != 0) {
                            hasOpaquePixel = true
                            break
                        }
                    }
                    if (hasOpaquePixel) break
                }
                require(hasOpaquePixel) { "Quadro do helicóptero transparente: $index" }
            }
            return Sprite(pixels, w, h, frames)
        } finally {
            image.recycle()
        }
    }
}
