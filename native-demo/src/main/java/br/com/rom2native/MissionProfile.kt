package br.com.rom2native

import org.json.JSONObject
import java.nio.charset.CodingErrorAction
import java.nio.ByteBuffer
import java.nio.charset.StandardCharsets

/**
 * Human-authored mission configuration; NOT a decompilation of SNES mission data.
 * Never loads code or resources from the JSON. The native engine revalidates
 * target count, coordinates, health and patrol ranges independently.
 */
object MissionProfile {
    private const val MAX_BYTES = 32768
    data class Mission(val title:String,val targets:IntArray,val count:Int)

    private fun integer(o:JSONObject,key:String):Int {
        val value=o.get(key)
        return when(value) {
            is Int -> value
            is Long -> {
                require(value in Int.MIN_VALUE..Int.MAX_VALUE){"Número muito grande: $key"}
                value.toInt()
            }
            else -> error("Esperado número inteiro em $key")
        }
    }

    fun parse(bytes:ByteArray,expectedRomHash:String):Mission {
        require(bytes.size in 1..MAX_BYTES){"Arquivo de missão deve ter no máximo 32 KiB"}
        val decoder=StandardCharsets.UTF_8.newDecoder()
            .onMalformedInput(CodingErrorAction.REPORT)
            .onUnmappableCharacter(CodingErrorAction.REPORT)
        val json=JSONObject(decoder.decode(ByteBuffer.wrap(bytes)).toString())
        require(json.optString("format")=="rom2native-mission-v1") {
            "Formato de missão incompatível"
        }
        require(json.optString("rom_sha256")==expectedRomHash) {
            "Missão criada para outra revisão da ROM"
        }
        require(json.optString("goal")=="destroy_all") {
            "Objetivo ainda não suportado. Use destroy_all"
        }
        val title=json.getString("title").trim()
        require(title.length in 1..70){"Título da missão deve ter 1 a 70 caracteres"}
        val list=json.getJSONArray("targets")
        require(list.length() in 1..12){"A missão deve conter entre 1 e 12 alvos"}
        val seen=mutableSetOf<String>()
        val data=IntArray(list.length()*5)
        for(i in 0 until list.length()){
            val obj=list.getJSONObject(i)
            val id=obj.getString("id")
            require(Regex("[A-Za-z0-9_-]{1,24}").matches(id) && seen.add(id)){
                "ID de alvo inválido ou repetido: $id"
            }
            val kind=when(obj.getString("type")){
                "depot" -> 0
                "turret" -> 1
                "patrol" -> 2
                else -> error("Tipo de alvo desconhecido: "+obj.getString("type"))
            }
            val x=integer(obj,"x")
            val y=integer(obj,"y")
            val hp=integer(obj,"hp")
            val radius=if(obj.has("patrol_range")) integer(obj,"patrol_range") else 0
            require(x in 22..298 && y in 34..218){
                "Posição fora dos limites do cenário: $id"
            }
            require(hp in 1..9){"Vida inválida: $id"}
            require((kind==2 && radius in 8..32) || (kind!=2 && radius==0)){
                "Alcance de patrulha inválido: $id"
            }
            require(x-radius>=18 && x+radius<=302){
                "Patrulha excede os limites: $id"
            }
            for(j in 0 until i){
                val dx=x-data[j*5]
                val dy=y-data[j*5+1]
                require(dx*dx+dy*dy>=26*26){"Alvos muito próximos: $id"}
            }
            val start=i*5
            data[start]=x
            data[start+1]=y
            data[start+2]=hp
            data[start+3]=kind
            data[start+4]=radius
        }
        return Mission(title,data,list.length())
    }
}
