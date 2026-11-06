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
    external fun status():String
}
