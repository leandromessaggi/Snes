package br.com.desertstrike

import android.app.Activity
import android.app.AlertDialog
import android.content.Intent
import android.media.AudioAttributes
import android.media.AudioFormat
import android.media.AudioTrack
import android.os.Bundle
import android.os.SystemClock
import android.view.InputDevice
import android.view.KeyEvent
import android.view.MotionEvent
import android.view.View
import android.widget.Toast
import java.io.File
import java.util.concurrent.atomic.AtomicBoolean
import kotlin.math.abs
import kotlin.math.max

/** Android host for the Snes9x Libretro core. Not a rewritten/native game engine. */
class MainActivity : Activity() {
    private lateinit var gameView: GameView
    private val active = AtomicBoolean(false)
    @Volatile private var playing = false
    private var gameThread: Thread? = null
    private var audioThread: Thread? = null
    private var track: AudioTrack? = null
    private var rom: ByteArray? = null
    private var romHash = ""
    private var currentHash = ""
    private var sampleRate = 32040
    private var frameNanos = 16_666_667L
    private var starting = false
    private var menuVisible = false
    private data class InstalledMod(val filename: String, val patch: ByteArray, var enabled: Boolean)
    private val mods = arrayListOf<InstalledMod>()
    private val mapping = hashMapOf<Int, Int>()
    private val pressed = hashSetOf<Int>()
    private var touchMask = 0
    private var analogMask = 0
    private var remapTarget: Int? = null
    private var traceExport: String? = null

    private val PICK_ROM = 201
    private val PICK_IPS = 202
    private val PICK_PACK = 203
    private val SAVE_TRACE = 204

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        window.decorView.systemUiVisibility = View.SYSTEM_UI_FLAG_FULLSCREEN or
            View.SYSTEM_UI_FLAG_HIDE_NAVIGATION or View.SYSTEM_UI_FLAG_IMMERSIVE_STICKY
        gameView = GameView(this, { showMenu() }, { touchMask = it; updatePad() })
        setContentView(gameView)
        defaultMapping()
        restoreMapping()
        val stored = File(filesDir, "original.sfc")
        if (stored.isFile) try {
            val bytes = stored.readBytes()
            RomIdentity.check(bytes)
            rom = bytes; romHash = RomIdentity.digest(bytes); loadMods()
        } catch (_: Exception) { rom = null }
        showMenu()
    }

    private fun toast(message: String) = Toast.makeText(this, message, Toast.LENGTH_LONG).show()
    private fun modDirectory(): File = File(filesDir, "mods_$romHash")
    private fun loadMods() {
        mods.clear()
        val prefs = getSharedPreferences("mods_$romHash", MODE_PRIVATE)
        modDirectory().listFiles()?.filter { it.isFile && it.extension.equals("ips", true) }
            ?.sortedBy { it.name }?.forEach { file ->
                try { mods.add(InstalledMod(file.name, file.readBytes(), prefs.getBoolean(file.name, true))) }
                catch (_: Exception) {}
            }
    }
    private fun clearMods() {
        mods.clear()
        modDirectory().listFiles()?.forEach { it.delete() }
        getSharedPreferences("mods_$romHash", MODE_PRIVATE).edit().clear().apply()
    }

    private fun defaultMapping() {
        mapping.clear()
        mapping[KeyEvent.KEYCODE_DPAD_UP] = Pad.UP
        mapping[KeyEvent.KEYCODE_DPAD_DOWN] = Pad.DOWN
        mapping[KeyEvent.KEYCODE_DPAD_LEFT] = Pad.LEFT
        mapping[KeyEvent.KEYCODE_DPAD_RIGHT] = Pad.RIGHT
        mapping[KeyEvent.KEYCODE_BUTTON_A] = Pad.B
        mapping[KeyEvent.KEYCODE_BUTTON_B] = Pad.A
        mapping[KeyEvent.KEYCODE_BUTTON_X] = Pad.Y
        mapping[KeyEvent.KEYCODE_BUTTON_Y] = Pad.X
        mapping[KeyEvent.KEYCODE_BUTTON_L1] = Pad.L
        mapping[KeyEvent.KEYCODE_BUTTON_R1] = Pad.R
        mapping[KeyEvent.KEYCODE_BUTTON_SELECT] = Pad.SELECT
        mapping[KeyEvent.KEYCODE_BUTTON_START] = Pad.START
    }
    private fun restoreMapping() {
        val prefs = getSharedPreferences("controls", MODE_PRIVATE)
        if (prefs.getBoolean("mapping_custom", false)) {
            mapping.clear()
            prefs.all.forEach { (key, value) ->
                val code = key.removePrefix("map_").toIntOrNull()
                if (key.startsWith("map_") && code != null && value is Int && value in 0..11)
                    mapping[code] = value
            }
        }
        gameView.touchVisible = prefs.getBoolean("touch", true)
    }
    private fun updatePad() {
        var bits = touchMask or analogMask
        synchronized(pressed) { pressed.forEach { mapping[it]?.let { id -> bits = bits or Pad.bit(id) } } }
        NativeCore.input(bits)
    }
    override fun onKeyDown(keyCode: Int, event: KeyEvent): Boolean {
        remapTarget?.let { target ->
            mapping.entries.removeAll { it.value == target }
            mapping[keyCode] = target
            val editor = getSharedPreferences("controls", MODE_PRIVATE).edit().clear()
            editor.putBoolean("mapping_custom", true)
            mapping.forEach { (k,v) -> editor.putInt("map_$k", v) }
            editor.apply()
            remapTarget = null
            toast("Controle remapeado")
            showMenu()
            return true
        }
        if (menuVisible) return super.onKeyDown(keyCode, event)
        if (keyCode == KeyEvent.KEYCODE_MENU) { showMenu(); return true }
        if (!mapping.containsKey(keyCode)) return super.onKeyDown(keyCode, event)
        synchronized(pressed) { pressed.add(keyCode) }
        updatePad()
        return true
    }
    override fun onKeyUp(keyCode: Int, event: KeyEvent): Boolean {
        if (menuVisible) return super.onKeyUp(keyCode, event)
        if (!mapping.containsKey(keyCode)) return super.onKeyUp(keyCode, event)
        synchronized(pressed) { pressed.remove(keyCode) }
        updatePad()
        return true
    }
    override fun onGenericMotionEvent(event: MotionEvent): Boolean {
        if (menuVisible || event.action != MotionEvent.ACTION_MOVE ||
            event.source and InputDevice.SOURCE_JOYSTICK != InputDevice.SOURCE_JOYSTICK)
            return super.onGenericMotionEvent(event)
        val hx = event.getAxisValue(MotionEvent.AXIS_HAT_X)
        val hy = event.getAxisValue(MotionEvent.AXIS_HAT_Y)
        val x = if (abs(hx) > .5f) hx else event.getAxisValue(MotionEvent.AXIS_X)
        val y = if (abs(hy) > .5f) hy else event.getAxisValue(MotionEvent.AXIS_Y)
        analogMask = (if (x < -.45f) Pad.bit(Pad.LEFT) else if (x > .45f) Pad.bit(Pad.RIGHT) else 0) or
            (if (y < -.45f) Pad.bit(Pad.UP) else if (y > .45f) Pad.bit(Pad.DOWN) else 0)
        updatePad()
        return true
    }

    private fun showMenu() {
        if (isFinishing || isDestroyed) return
        val wasPlaying = playing
        playing = false
        menuVisible = true
        touchMask = 0; analogMask = 0
        synchronized(pressed) { pressed.clear() }
        updatePad()
        val items = arrayOf("Abrir ROM", "Jogar / Continuar", "Adicionar IPS", "Importar ZIP de mods",
            "Ativar/desativar mods", "Remover mods", "Salvar estado", "Carregar estado",
            "Mostrar/esconder controle touch", "Remapear gamepad", "Reiniciar",
            "Iniciar rastreamento de RAM", "Exportar rastreamento JSON", "Diagnóstico técnico")
        AlertDialog.Builder(this).setTitle("Desert Strike Android v0.10 — experimental")
            .setItems(items) { _, index ->
                when (index) {
                    0 -> { stopCore(); picker(PICK_ROM) }
                    1 -> { menuVisible = false; launch() }
                    2 -> { stopCore(); picker(PICK_IPS) }
                    3 -> { stopCore(); picker(PICK_PACK) }
                    4 -> editMods()
                    5 -> { stopCore(); clearMods(); toast("Mods removidos"); showMenu() }
                    6 -> { saveState(); showMenu() }
                    7 -> { loadState(); showMenu() }
                    8 -> {
                        gameView.touchVisible = !gameView.touchVisible
                        getSharedPreferences("controls", MODE_PRIVATE).edit()
                            .putBoolean("touch", gameView.touchVisible).apply()
                        menuVisible = false
                        if (wasPlaying && active.get()) playing = true else showMenu()
                    }
                    9 -> selectRemap()
                    10 -> { stopCore(); menuVisible = false; launch() }
                    11 -> {
                        if (active.get() && NativeCore.traceStart()) {
                            menuVisible = false; playing = true
                            toast("Rastreando alterações da RAM por até 600 quadros")
                        } else { toast("Inicie o jogo antes"); showMenu() }
                    }
                    12 -> {
                        traceExport = NativeCore.traceStop()
                        if (traceExport == null) { toast("Nenhum rastreamento disponível"); showMenu() }
                        else picker(SAVE_TRACE)
                    }
                    13 -> {
                        val core = File(applicationInfo.nativeLibraryDir, "libsnes9x_libretro.so")
                        AlertDialog.Builder(this).setTitle("Diagnóstico")
                            .setMessage("ROM: ${rom?.size ?: 0} bytes\nCore Snes9x: ${core.exists()}\nAtivo: ${active.get()}\nMods: ${mods.size}\nABI: ${android.os.Build.SUPPORTED_ABIS.joinToString()}\nMétricas JNI: ${NativeCore.stats()}")
                            .setPositiveButton("OK") { _, _ -> showMenu() }.show()
                    }
                }
            }
            .setOnCancelListener { menuVisible = false; if (wasPlaying && active.get()) playing = true }
            .show()
    }

    private fun editMods() {
        if (mods.isEmpty()) { toast("Nenhum mod"); showMenu(); return }
        val checks = BooleanArray(mods.size) { mods[it].enabled }
        AlertDialog.Builder(this).setTitle("Mods ativos (ordem de nome)")
            .setMultiChoiceItems(mods.map { it.filename }.toTypedArray(), checks) { _, i, v -> checks[i] = v }
            .setPositiveButton("Aplicar") { _, _ ->
                try {
                    var candidate = rom?.copyOf() ?: error("ROM ausente")
                    mods.forEachIndexed { i, mod -> if (checks[i]) candidate = IpsPatcher.apply(candidate, mod.patch) }
                    stopCore()
                    val edit = getSharedPreferences("mods_$romHash", MODE_PRIVATE).edit()
                    mods.forEachIndexed { i, mod -> mod.enabled = checks[i]; edit.putBoolean(mod.filename, checks[i]) }
                    edit.apply()
                    toast("Mods atualizados; reinicie o jogo")
                } catch (e: Exception) { toast("Falha nos mods: ${e.message}") }
                showMenu()
            }.setNegativeButton("Cancelar") { _, _ -> showMenu() }.show()
    }
    private fun selectRemap() {
        val names = arrayOf("↑", "↓", "←", "→", "B", "A", "Y", "X", "L", "R", "SELECT", "START")
        val ids = intArrayOf(Pad.UP, Pad.DOWN, Pad.LEFT, Pad.RIGHT, Pad.B, Pad.A, Pad.Y, Pad.X, Pad.L, Pad.R, Pad.SELECT, Pad.START)
        AlertDialog.Builder(this).setTitle("Escolha um botão SNES")
            .setItems(names) { _, index ->
                val target = ids[index]
                AlertDialog.Builder(this).setTitle("Pressione o botão físico")
                    .setOnKeyListener { dialog, key, event ->
                        if (event.action != KeyEvent.ACTION_DOWN) false else {
                            remapTarget = target
                            onKeyDown(key, event)
                            dialog.dismiss()
                            true
                        }
                    }
                    .setNegativeButton("Cancelar") { _, _ -> showMenu() }
                    .setOnCancelListener { remapTarget = null; showMenu() }.show()
            }.setNegativeButton("Voltar") { _, _ -> showMenu() }.show()
    }
    private fun picker(type: Int) {
        val intent = Intent(if (type == SAVE_TRACE) Intent.ACTION_CREATE_DOCUMENT else Intent.ACTION_OPEN_DOCUMENT)
        intent.addCategory(Intent.CATEGORY_OPENABLE)
        intent.type = if (type == SAVE_TRACE) "application/json" else "*/*"
        if (type == SAVE_TRACE) intent.putExtra(Intent.EXTRA_TITLE, "desert-strike-wram-trace.json")
        @Suppress("DEPRECATION")
        startActivityForResult(intent, type)
    }
    @Deprecated("Uses Android's document picker")
    override fun onActivityResult(requestCode: Int, resultCode: Int, data: Intent?) {
        super.onActivityResult(requestCode, resultCode, data)
        if (resultCode != RESULT_OK || data?.data == null) { showMenu(); return }
        try {
            val uri = data.data!!
            when (requestCode) {
                PICK_ROM -> {
                    val bytes = RomLoader.read(this, uri)
                    RomIdentity.check(bytes)
                    File(filesDir, "original.sfc").writeBytes(bytes)
                    rom = bytes
                    romHash = RomIdentity.digest(bytes)
                    loadMods()
                    toast("ROM validada")
                }
                PICK_IPS -> {
                    val patch = contentResolver.openInputStream(uri)?.use { RomLoader.readCapped(it, 2*1024*1024) }
                        ?: error("Patch ausente")
                    installPatches(listOf("IPS" to patch))
                }
                PICK_PACK -> {
                    val pack = contentResolver.openInputStream(uri)?.use { ModPack.parse(it, rom ?: error("ROM ausente")) }
                        ?: error("ZIP ausente")
                    installPatches(pack.patches.map { it.label to it.bytes })
                }
                SAVE_TRACE -> {
                    val text = traceExport ?: error("Rastreamento ausente")
                    contentResolver.openOutputStream(uri, "w")?.use { it.write(text.toByteArray()) }
                        ?: error("Destino indisponível")
                    traceExport = null
                    toast("Rastreamento exportado")
                }
            }
        } catch (e: Exception) { toast("Erro: ${e.message}") }
        showMenu()
    }
    private fun installPatches(items: List<Pair<String, ByteArray>>) {
        var candidate = rom?.copyOf() ?: error("ROM ausente")
        mods.filter { it.enabled }.forEach { candidate = IpsPatcher.apply(candidate, it.patch) }
        items.forEach { candidate = IpsPatcher.apply(candidate, it.second) }
        val dir = modDirectory().apply { mkdirs() }
        var n = (dir.listFiles()?.size ?: 0) + 1
        items.forEach { (label, bytes) ->
            val safe = label.replace(Regex("[^a-zA-Z0-9_-]"), "_").take(30)
            val name = "patch_${(n++).toString().padStart(4, '0')}_$safe.ips"
            File(dir, name).writeBytes(bytes)
            mods.add(InstalledMod(name, bytes, true))
        }
        toast("Instalados ${items.size} patches")
    }

    private fun launch() {
        if (active.get()) { menuVisible = false; playing = true; return }
        val original = rom ?: run { toast("Importe a ROM primeiro"); showMenu(); return }
        if (starting) return
        starting = true
        try {
            var candidate = original
            mods.filter { it.enabled }.forEach { candidate = IpsPatcher.apply(candidate, it.patch) }
            currentHash = RomIdentity.digest(candidate)
            val core = File(applicationInfo.nativeLibraryDir, "libsnes9x_libretro.so")
            check(core.exists()) { "Núcleo Snes9x ausente" }
            val frequency = NativeCore.start(core.absolutePath, filesDir.absolutePath, candidate)
            check(frequency > 0) { "Erro Libretro: ${NativeCore.lastError()}" }
            sampleRate = frequency.toInt().coerceIn(8000, 96000)
            val fps = NativeCore.fps().takeIf { it in 30.0..120.0 } ?: 60.0
            frameNanos = (1_000_000_000.0 / fps).toLong()
            File(filesDir, "$currentHash.srm").takeIf { it.exists() }?.let { NativeCore.loadRam(it.readBytes()) }
            active.set(true)
            menuVisible = false
            playing = true
            startAudio()
            gameThread = Thread({ gameLoop() }, "desert-video").apply { start() }
        } catch (e: Exception) {
            active.set(false); playing = false
            stopWorkers()
            NativeCore.stop()
            toast("Falha ao iniciar: ${e.message}")
            showMenu()
        } finally { starting = false }
    }
    private fun startAudio() {
        try {
            val minBytes = AudioTrack.getMinBufferSize(sampleRate, AudioFormat.CHANNEL_OUT_STEREO, AudioFormat.ENCODING_PCM_16BIT)
            check(minBytes > 0) { "Áudio não suportado" }
            val output = AudioTrack.Builder()
                .setAudioAttributes(AudioAttributes.Builder().setUsage(AudioAttributes.USAGE_GAME).setContentType(AudioAttributes.CONTENT_TYPE_MUSIC).build())
                .setAudioFormat(AudioFormat.Builder().setSampleRate(sampleRate).setEncoding(AudioFormat.ENCODING_PCM_16BIT).setChannelMask(AudioFormat.CHANNEL_OUT_STEREO).build())
                .setBufferSizeInBytes(max(minBytes, 4096))
                .setTransferMode(AudioTrack.MODE_STREAM).build()
            if (output.state != AudioTrack.STATE_INITIALIZED) { output.release(); error("AudioTrack indisponível") }
            output.play()
            track = output
            audioThread = Thread({
                val samples = ShortArray(2048)
                while (active.get() && !Thread.currentThread().isInterrupted) {
                    if (!playing) { SystemClock.sleep(8); continue }
                    val n = NativeCore.drainAudio(samples)
                    if (n > 0) {
                        try { if (output.write(samples, 0, n, AudioTrack.WRITE_BLOCKING) < 0) break }
                        catch (_: Exception) { break }
                    } else SystemClock.sleep(3)
                }
            }, "desert-audio").apply { start() }
        } catch (e: Exception) { toast("Áudio indisponível: ${e.message}") }
    }
    private fun gameLoop() {
        val step = frameNanos
        var next = System.nanoTime()
        while (active.get()) {
            if (!playing) { next = System.nanoTime(); SystemClock.sleep(10); continue }
            val encoded = NativeCore.frame(gameView.pixelBuffer())
            if (encoded != 0) gameView.updateFrame(encoded)
            next += step
            val wait = next - System.nanoTime()
            if (wait > 0) SystemClock.sleep(wait / 1_000_000L)
            else if (wait < -step * 4) next = System.nanoTime()
        }
    }
    private fun stateFile() = File(filesDir, "$currentHash.state")
    private fun saveState() {
        if (!active.get()) { toast("Inicie o jogo"); return }
        try { stateFile().writeBytes(NativeCore.saveState() ?: error("Save indisponível")); toast("Estado salvo") }
        catch (e: Exception) { toast("Falha: ${e.message}") }
    }
    private fun loadState() {
        if (!active.get()) { toast("Inicie o jogo"); return }
        try { check(NativeCore.loadState(stateFile().readBytes())); toast("Estado restaurado") }
        catch (e: Exception) { toast("Falha: ${e.message}") }
    }
    private fun stopWorkers() {
        audioThread?.interrupt()
        try { track?.pause(); track?.flush() } catch (_: Exception) {}
        try { gameThread?.join(1500); audioThread?.join(1500) }
        catch (_: InterruptedException) { Thread.currentThread().interrupt() }
        gameThread = null; audioThread = null
        try { track?.release() } catch (_: Exception) {}
        track = null
    }
    private fun stopCore() {
        playing = false
        val wasActive = active.getAndSet(false)
        stopWorkers()
        if (wasActive) {
            try {
                if (currentHash.isNotBlank()) NativeCore.saveRam()?.let { File(filesDir, "$currentHash.srm").writeBytes(it) }
            } catch (_: Exception) {}
            NativeCore.stop()
        }
    }
    override fun onPause() {
        playing = false
        synchronized(pressed) { pressed.clear() }
        touchMask = 0; analogMask = 0; updatePad()
        if (active.get()) try {
            NativeCore.saveRam()?.let { File(filesDir, "$currentHash.srm").writeBytes(it) }
        } catch (_: Exception) {}
        super.onPause()
    }
    override fun onResume() { super.onResume(); if (active.get() && !menuVisible) playing = true }
    override fun onDestroy() { stopCore(); super.onDestroy() }
    @Deprecated("Back opens menu")
    override fun onBackPressed() { if (!menuVisible) showMenu() }
}
