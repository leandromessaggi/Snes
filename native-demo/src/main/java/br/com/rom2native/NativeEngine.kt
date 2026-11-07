package br.com.rom2native

object NativeEngine {
    init { System.loadLibrary("rom_native") }
    external fun importRom(bytes:ByteArray):Boolean
    external fun step(mask:Int,seconds:Float)
    external fun setHelicopterSprite(argb:IntArray,width:Int,height:Int):Boolean
    external fun draw(pixels:IntArray)
    external fun setHelicopterAtlas(argb:IntArray,width:Int,height:Int,frames:Int):Boolean
    external fun setSceneImage(argb:IntArray,width:Int,height:Int):Boolean
    external fun clearSceneImage()
    /** Each target is [x,y,hp,type(0 depot/1 turret/2 patrol),patrolRange]. */
    external fun configureMission(data:IntArray,count:Int):Boolean
    external fun defaultMission()
    external fun restartMission()
    /** [health, targetsDestroyed, targetTotal, status(0 playing,1 won,2 lost)]. */
    external fun missionStats():IntArray
    external fun status():String
}
