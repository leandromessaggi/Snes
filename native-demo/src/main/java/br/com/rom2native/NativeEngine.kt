package br.com.rom2native

object NativeEngine {
    init { System.loadLibrary("rom_native") }
    external fun importRom(bytes:ByteArray):Boolean
    external fun step(mask:Int,seconds:Float)
    external fun draw(pixels:IntArray)
    external fun status():String
}
