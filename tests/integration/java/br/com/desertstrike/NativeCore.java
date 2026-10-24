package br.com.desertstrike;
public final class NativeCore {
    static { System.loadLibrary("desert_bridge"); }
    public native double start(String path,String dir,byte[] rom);
    public native String lastError();
    public native double fps();
    public native void stop();
    public native int frame(int[] pixels);
    public native void input(int bits);
    public native int drainAudio(short[] samples);
    public native byte[] saveState();
    public native boolean loadState(byte[] state);
    public native byte[] saveRam();
    public native boolean loadRam(byte[] ram);
    public native boolean traceStart();
    public native String traceStop();
}
