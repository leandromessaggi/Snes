package br.com.desertstrike;
import java.io.File;
import java.util.Arrays;

public final class JniSmokeJava {
    private static void check(boolean ok,String msg) { if (!ok) throw new AssertionError(msg); }
    public static void main(String[] args) {
        NativeCore core=new NativeCore();
        String path=new File(args[0]).getAbsolutePath();
        check(core.start("/missing/core.so","/tmp",new byte[128])==0.0,"Loader error");
        check(!core.lastError().isEmpty(),"Expected diagnostic");
        check(core.start(path,"/tmp",new byte[8])==0.0,"Invalid mock ROM");
        for(int format=0;format<3;format++) {
            byte[] rom=new byte[128]; rom[0]=(byte)format;
            check(core.start(path,"/tmp",rom)==32000.0,"Sample rate");
            check(core.fps()==60.0,"FPS");
            check(core.traceStart(),"WRAM tracing");
            int[] pixels=new int[512*512];
            check(core.frame(pixels)==((2<<16)|2),"Frame shape");
            check(pixels[0]==0xffff0000 && pixels[1]==0xff00ff00 && pixels[2]==0xff0000ff,"Pixels");
            short[] samples=new short[32];
            check(core.drainAudio(samples)==10,"Audio samples");
            check(samples[0]==-1 && samples[1]==1 && samples[8]==-123 && samples[9]==456,"Audio data");
            core.input(0x181); core.frame(pixels);
            String trace=core.traceStop();
            check(trace!=null && trace.contains("\"pad\":385"),"Controller input");
            byte[] state=core.saveState();
            check(state!=null && state.length>0 && core.loadState(state),"State round-trip");
            byte[] sram=new byte[16]; Arrays.fill(sram,(byte)0x5a);
            check(core.loadRam(sram) && Arrays.equals(sram,core.saveRam()),"SRAM");
            core.stop();
            check(core.frame(pixels)==0,"Stop lifecycle");
            System.out.println("PASS Java JNI mock format "+format);
        }
    }
}
