package br.com.desertstrike

import org.json.JSONObject
import java.io.ByteArrayOutputStream
import java.io.InputStream
import java.security.MessageDigest
import java.util.zip.ZipInputStream

/** Imports IPS/BPS modpacks into memory; never executes third-party code. */
object ModPack {
    data class Patch(val label: String, val bytes: ByteArray)
    data class Contents(val name: String, val patches: List<Patch>)
    private const val MAX_FILE = 2 * 1024 * 1024
    private const val MAX_TOTAL = 8 * 1024 * 1024
    private const val MAX_ENTRIES = 64

    private fun limitedRead(input: InputStream, sizeLimit: Int): ByteArray {
        val result = ByteArrayOutputStream()
        val temp = ByteArray(8192)
        while (true) {
            val read = input.read(temp)
            if (read == -1) return result.toByteArray()
            if (read > 0) {
                require(result.size().toLong() + read <= sizeLimit) { "Arquivo do pacote excede limite" }
                result.write(temp, 0, read)
            }
        }
    }
    fun parse(input: InputStream, originalRom: ByteArray): Contents {
        val files = LinkedHashMap<String, ByteArray>()
        var total = 0
        ZipInputStream(input).use { zip ->
            while (true) {
                val entry = zip.nextEntry ?: break
                if (entry.isDirectory) continue
                require(files.size < MAX_ENTRIES) { "Pacote contém arquivos demais" }
                val name = entry.name
                require(name.isNotBlank() && !name.startsWith('/') && !name.contains('\\') &&
                        name.split('/').none { it == ".." || it.isBlank() }) { "Nome de arquivo inválido" }
                require(!files.containsKey(name)) { "Arquivo duplicado: $name" }
                val contents = limitedRead(zip, MAX_FILE)
                total += contents.size
                require(total <= MAX_TOTAL) { "Pacote excede limite de 8 MiB" }
                files[name] = contents
                zip.closeEntry()
            }
        }
        val manifest = files["manifest.json"]?.let { JSONObject(String(it, Charsets.UTF_8)) }
            ?: error("Pacote sem manifest.json")
        val displayName = manifest.optString("name").trim().take(70)
        require(displayName.isNotBlank()) { "Pacote sem nome" }
        val targetHash = manifest.optString("target_sha256").trim().lowercase()
        val hash = MessageDigest.getInstance("SHA-256").digest(originalRom)
            .joinToString("") { "%02x".format(it) }
        require(targetHash == hash) { "Mod incompatível com o SHA-256 desta ROM" }
        val list = manifest.optJSONArray("patches") ?: error("Pacote sem lista de patches")
        require(list.length() in 1..16) { "Pacote deve conter de 1 a 16 patches" }
        var resultingRom = originalRom.copyOf()
        val patches = ArrayList<Patch>()
        for (i in 0 until list.length()) {
            val key = list.getString(i)
            require(ModPatcher.supported(key)) { "Mod deve ser IPS ou BPS: $key" }
            val data = files[key] ?: error("Patch ausente no pacote: $key")
            resultingRom = ModPatcher.apply(resultingRom, data)
            patches.add(Patch("$displayName · ${key.substringAfterLast('/')}", data))
        }
        return Contents(displayName, patches)
    }
}
