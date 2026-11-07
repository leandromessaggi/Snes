package br.com.rom2native

import android.graphics.BitmapFactory
import org.json.JSONObject
import java.io.ByteArrayOutputStream
import java.security.MessageDigest
import java.util.zip.ZipInputStream

/**
 * Data-only asset packs: v1 one helicopter, v2 eight directions,
 * v3 helicopter + background. The ZIP may never contain executable code.
 */
object VisualPack {
    data class Scene(val pixels:IntArray, val width:Int, val height:Int)
    data class Sprite(val pixels:IntArray, val width:Int, val height:Int,
                      val frames:Int, val scene:Scene? = null)
    private const val MAX_PACK = 5 * 1024 * 1024
    private const val MAX_IMAGE = 2 * 1024 * 1024
    private const val MAX_MANIFEST = 8192
    private const val V1 = "rom2native-visual-v1"
    private const val V2 = "rom2native-visual-v2"
    private const val V3 = "rom2native-visual-v3"
    private val DIRECTIONS = arrayOf("N","NE","E","SE","S","SW","W","NW")

    private fun readLimited(zip:ZipInputStream,max:Int):ByteArray {
        val out=ByteArrayOutputStream()
        val buffer=ByteArray(8192)
        while(true) {
            val count=zip.read(buffer)
            if(count<0) break
            if(count==0) continue
            require(out.size().toLong()+count<=max){"Entrada ZIP excede limite"}
            out.write(buffer,0,count)
        }
        return out.toByteArray()
    }
    private fun sha256(data:ByteArray):String =
        MessageDigest.getInstance("SHA-256").digest(data)
            .joinToString(""){"%02x".format(it)}

    // Strictly require 8-bit RGBA PNG, not a magic-header-only substitute.
    private fun rgbaPixels(png:ByteArray,widthLimit:Int,heightLimit:Int):Triple<IntArray,Int,Int> {
        require(png.size in 33..MAX_IMAGE){"Imagem muito grande ou inválida"}
        val sig=byteArrayOf(0x89.toByte(),0x50,0x4e,0x47,0x0d,0x0a,0x1a,0x0a)
        require(png.copyOfRange(0,8).contentEquals(sig) &&
            (png[24].toInt() and 255)==8 && (png[25].toInt() and 255)==6) {
            "É obrigatório PNG RGBA 8 bits"
        }
        val bounds=BitmapFactory.Options().apply { inJustDecodeBounds=true }
        BitmapFactory.decodeByteArray(png,0,png.size,bounds)
        val w=bounds.outWidth
        val h=bounds.outHeight
        require(w in 1..widthLimit && h in 1..heightLimit){"Dimensões de PNG fora do limite"}
        val options=BitmapFactory.Options().apply {
            inScaled=false
            inPremultiplied=false
        }
        val bitmap=BitmapFactory.decodeByteArray(png,0,png.size,options)
            ?: error("PNG inválido ou corrompido")
        try {
            require(bitmap.width==w && bitmap.height==h){"Imagem com dimensões inconsistentes"}
            val values=IntArray(w*h)
            bitmap.getPixels(values,0,w,0,0,w,h)
            return Triple(values,w,h)
        } finally {
            bitmap.recycle()
        }
    }

    fun parse(bytes:ByteArray,expectedRomHash:String):Sprite {
        require(bytes.size in 1..MAX_PACK){"Pacote visual excede 5 MiB"}
        val entries=linkedMapOf<String,ByteArray>()
        ZipInputStream(bytes.inputStream()).use {zip->
            while(true) {
                val entry=zip.nextEntry ?: break
                require(!entry.isDirectory){"Diretório não permitido"}
                val name=entry.name
                require(name=="manifest.json" || name=="helicopter.png" || name=="background.png") {
                    "Pacote contém arquivo inesperado"
                }
                require(!entries.containsKey(name)){"Arquivo ZIP duplicado"}
                val limit=if(name=="manifest.json") MAX_MANIFEST else MAX_IMAGE
                entries[name]=readLimited(zip,limit)
                zip.closeEntry()
            }
        }
        val manifest=JSONObject(String(entries["manifest.json"]
            ?: error("manifest.json ausente"),Charsets.UTF_8))
        val format=manifest.optString("format")
        require(format==V1 || format==V2 || format==V3){"Versão de pacote desconhecida"}
        val needsScene=format==V3
        val expected=if(needsScene)
            setOf("manifest.json","helicopter.png","background.png")
        else setOf("manifest.json","helicopter.png")
        require(entries.keys==expected){"Arquivos do pacote não correspondem à versão"}
        require(manifest.optString("rom_sha256")==expectedRomHash) {
            "Pacote destinado a outra revisão da ROM"
        }

        val asset=manifest.getJSONObject("asset")
        require(asset.optString("id")=="helicopter" && asset.optString("file")=="helicopter.png") {
            "Identificador do helicóptero inválido"
        }
        val heli=entries.getValue("helicopter.png")
        require(sha256(heli)==asset.optString("sha256")){"Hash do helicóptero incorreto"}
        val frames=if(format==V2) 8 else if(format==V3) asset.optInt("frames",1) else 1
        require(frames==1 || frames==8){"Número de quadros inválido"}
        val (pixels,w,h)=rgbaPixels(heli,128*frames,128)
        require(w%frames==0 && w/frames in 1..128 &&
            w==asset.getInt("width") && h==asset.getInt("height")) {
            "Dimensões do helicóptero divergentes"
        }
        if(frames==8) {
            require(asset.optInt("frames")==8 && asset.optString("layout")=="horizontal" &&
                asset.optInt("frame_width")==w/8 && asset.optInt("frame_height")==h) {
                "Atlas direcional incompatível"
            }
            val dirs=asset.getJSONArray("directions")
            require(dirs.length()==8 &&
                DIRECTIONS.indices.all{i->dirs.getString(i)==DIRECTIONS[i]}) {
                "Direções devem seguir N,NE,E,SE,S,SW,W,NW"
            }
        } else {
            require(!asset.has("frames") || asset.getInt("frames")==1) {
                "Sprite com quadros incompatíveis"
            }
        }
        val fw=w/frames
        for(index in 0 until frames) {
            var visible=false
            for(y in 0 until h) {
                for(x in 0 until fw) {
                    if((pixels[y*w+index*fw+x] ushr 24)!=0) {
                        visible=true
                        break
                    }
                }
                if(visible)break
            }
            require(visible){"Quadro do helicóptero invisível: $index"}
        }

        var scene:Scene?=null
        if(needsScene) {
            val info=manifest.getJSONObject("scene")
            require(info.optString("id")=="background" &&
                info.optString("file")=="background.png" &&
                info.optInt("width")==320 && info.optInt("height")==240) {
                "Metadados do cenário inválidos"
            }
            val png=entries.getValue("background.png")
            require(sha256(png)==info.optString("sha256")){"Hash do cenário inválido"}
            val (background,bw,bh)=rgbaPixels(png,320,240)
            require(bw==320 && bh==240){"Cenário precisa ser 320x240"}
            require(background.all{(it ushr 24)==255}) {
                "Cenário precisa ser completamente opaco"
            }
            scene=Scene(background,bw,bh)
        }
        return Sprite(pixels,w,h,frames,scene)
    }
}
