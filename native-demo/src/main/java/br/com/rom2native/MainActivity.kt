package br.com.rom2native

import android.app.Activity
import android.content.Intent
import android.os.Bundle
import android.view.KeyEvent
import android.view.View
import android.widget.Button
import android.widget.LinearLayout
import android.widget.TextView
import android.net.Uri
import java.io.ByteArrayOutputStream
import java.io.File
import java.security.MessageDigest
import java.util.zip.ZipInputStream

/** Independent Android host: there is NO emulator/libretro in this module. */
class MainActivity : Activity() {
    private lateinit var view: FlightView
    private lateinit var status: TextView
    private val down = mutableSetOf<Int>()
    private var pad = 0
    private val supportedHash = "606abf536440173ae36466db360c7db6b474beb7a105c8a62bc74a54cbe1c38b"

    override fun onCreate(state: Bundle?) {
        super.onCreate(state)
        val root=LinearLayout(this).apply { orientation=LinearLayout.VERTICAL }
        val importButton=Button(this).apply {
            text="Importar minha ROM SNES"
            setOnClickListener {
                val intent=Intent(Intent.ACTION_OPEN_DOCUMENT).apply {
                    type="*/*"
                    addCategory(Intent.CATEGORY_OPENABLE)
                }
                startActivityForResult(intent,101)
            }
        }
        val visualButton=Button(this).apply {
            text="Importar pacote visual (ZIP)"
            setOnClickListener {
                if (!view.loaded) {
                    status.text="Importe a ROM original antes do pacote visual"
                } else {
                    val intent=Intent(Intent.ACTION_OPEN_DOCUMENT).apply {
                        type="*/*" // Android providers often expose ZIPs as application/octet-stream
                        addCategory(Intent.CATEGORY_OPENABLE)
                    }
                    startActivityForResult(intent,102)
                }
            }
        }
        status=TextView(this).apply {
            text="Protótipo nativo: importe sua ROM para iniciar. Física e mapa são experimentais."
            setPadding(12,3,12,3)
        }
        view=FlightView(this,{pad})
        root.addView(importButton)
        root.addView(visualButton)
        root.addView(status)
        root.addView(view,LinearLayout.LayoutParams(-1,0,1f))
        setContentView(root)
        val saved=File(filesDir,"user.sfc")
        if(saved.isFile) try {
            val bytes=saved.readBytes()
            if(validate(bytes)) {
                view.loaded=NativeEngine.importRom(bytes)
                showStatus()
                restoreVisualPack()
            }
        } catch (_:Exception) { }
    }
    private fun applyVisualPack(sprite:VisualPack.Sprite) {
        if(sprite.scene!=null) {
            check(NativeEngine.setSceneImage(sprite.scene.pixels,
                sprite.scene.width,sprite.scene.height)){"Motor recusou o cenário"}
        } else {
            NativeEngine.clearSceneImage()
        }
        check(NativeEngine.setHelicopterAtlas(sprite.pixels,sprite.width,
            sprite.height,sprite.frames)){"Motor recusou o helicóptero"}
    }
    private fun restoreVisualPack() {
        val saved=File(filesDir,"visualpack.zip")
        if (!saved.isFile || !view.loaded) return
        try {
            val sprite=VisualPack.parse(saved.readBytes(),supportedHash)
            applyVisualPack(sprite)
            showStatus()
        } catch (e:Exception) {
            status.text="Pacote visual não carregado: "+e.message
        }
    }

    private fun showStatus() {
        status.text="MVP NATIVO • sem Snes9x • regras e cenário demonstrativos • "+NativeEngine.status()
    }
    private fun readCapped(stream:java.io.InputStream,max:Int):ByteArray {
        val output=ByteArrayOutputStream()
        val buf=ByteArray(8192)
        while(true) {
            val n=stream.read(buf)
            if(n<0) break
            if(n==0) continue
            require(output.size().toLong()+n<=max) { "Arquivo excede limite" }
            output.write(buf,0,n)
        }
        return output.toByteArray()
    }
    private fun readRom(uri:Uri):ByteArray {
        val raw=contentResolver.openInputStream(uri)?.use {readCapped(it,12*1024*1024)}
            ?: error("Arquivo não disponível")
        val src=if(raw.size>=2 && raw[0]==0x50.toByte() && raw[1]==0x4b.toByte()) {
            ZipInputStream(raw.inputStream()).use { zip ->
                var chosen:ByteArray?=null
                while(true) {
                    val item=zip.nextEntry ?: break
                    if(!item.isDirectory && (item.name.endsWith(".smc",true) || item.name.endsWith(".sfc",true))) {
                        chosen=readCapped(zip,2*1024*1024)
                        break
                    }
                }
                chosen ?: error("ZIP sem ROM .smc/.sfc")
            }
        } else raw
        return if(src.size%1024==512) src.copyOfRange(512,src.size) else src
    }
    private fun validate(bytes:ByteArray):Boolean {
        if(bytes.size!=1024*1024)return false
        val hash=MessageDigest.getInstance("SHA-256").digest(bytes)
            .joinToString(""){"%02x".format(it)}
        return hash==supportedHash
    }
    @Deprecated("Uses Android document picker")
    override fun onActivityResult(requestCode:Int,resultCode:Int,data:Intent?) {
        super.onActivityResult(requestCode,resultCode,data)
        if ((requestCode!=101 && requestCode!=102) || resultCode!=RESULT_OK || data?.data==null) return
        try {
            when (requestCode) {
                101 -> {
                    val raw=readRom(data.data!!)
                    require(validate(raw)){"ROM diferente da edição analisada"}
                    check(NativeEngine.importRom(raw)){"O motor nativo recusou os dados"}
                    File(filesDir,"user.sfc").writeBytes(raw)
                    view.loaded=true
                    showStatus()
                    restoreVisualPack()
                }
                102 -> {
                    check(view.loaded){"Importe a ROM original antes"}
                    val pack=contentResolver.openInputStream(data.data!!)?.use {
                        readCapped(it,5*1024*1024)
                    } ?: error("Arquivo de pacote visual indisponível")
                    val sprite=VisualPack.parse(pack,supportedHash)
                    applyVisualPack(sprite)
                    File(filesDir,"visualpack.zip").writeBytes(pack)
                    showStatus()
                    status.text = status.text.toString() + " • pacote visual validado"
                    view.invalidate()
                }
            }
        } catch(ex:Exception) {
            status.text="Falha ao importar: "+ex.message
        }
    }
    fun setTouchMask(mask:Int) {
        pad=mask or keyMask()
    }
    private fun keyMask():Int {
        var bits=0
        for(key in down)bits=bits or when(key) {
            KeyEvent.KEYCODE_DPAD_UP -> 1 shl 4
            KeyEvent.KEYCODE_DPAD_DOWN -> 1 shl 5
            KeyEvent.KEYCODE_DPAD_LEFT -> 1 shl 6
            KeyEvent.KEYCODE_DPAD_RIGHT -> 1 shl 7
            KeyEvent.KEYCODE_BUTTON_A,KeyEvent.KEYCODE_BUTTON_R1,KeyEvent.KEYCODE_SPACE -> 1
            else -> 0
        }
        return bits
    }
    override fun onKeyDown(code:Int,event:KeyEvent):Boolean {
        if (code in supportedKeys) {
            down.add(code)
            pad=pad or keyMask()
            return true
        }
        return super.onKeyDown(code,event)
    }
    override fun onKeyUp(code:Int,event:KeyEvent):Boolean {
        if(code in supportedKeys) {
            down.remove(code)
            pad=keyMask() or view.touchMask
            return true
        }
        return super.onKeyUp(code,event)
    }
    override fun onPause() {
        down.clear();pad=0
        view.touchMask=0
        super.onPause()
    }
    companion object {
        private val supportedKeys=setOf(
            KeyEvent.KEYCODE_DPAD_UP,KeyEvent.KEYCODE_DPAD_DOWN,
            KeyEvent.KEYCODE_DPAD_LEFT,KeyEvent.KEYCODE_DPAD_RIGHT,
            KeyEvent.KEYCODE_BUTTON_A,KeyEvent.KEYCODE_BUTTON_R1,KeyEvent.KEYCODE_SPACE)
    }
}
