#include <jni.h>
#include <dlfcn.h>
#include <cstdint>
#include <cstring>
#include <algorithm>
#include <atomic>
#include <mutex>
#include <string>
#include <vector>
#include "audio_ring.hpp"
#include "ram_trace.hpp"

// Minimal implementation of the public Libretro ABI.
// Core execution is single-threaded under coreMutex.
namespace {
struct GameInfo { const char* path; const void* data; size_t size; const char* meta; };
struct Geometry { unsigned base_width, base_height, max_width, max_height; float aspect_ratio; };
struct Timing { double fps, sample_rate; };
struct AVInfo { Geometry geometry; Timing timing; };
struct Variable { const char* key; const char* value; };
using Environment = bool (*)(unsigned, void*);
using Video = void (*)(const void*, unsigned, unsigned, size_t);
using Audio = void (*)(int16_t, int16_t);
using AudioBatch = size_t (*)(const int16_t*, size_t);
using InputPoll = void (*)();
using InputState = int16_t (*)(unsigned, unsigned, unsigned, unsigned);

struct Api {
    void (*set_environment)(Environment) = nullptr;
    void (*set_video_refresh)(Video) = nullptr;
    void (*set_audio_sample)(Audio) = nullptr;
    void (*set_audio_sample_batch)(AudioBatch) = nullptr;
    void (*set_input_poll)(InputPoll) = nullptr;
    void (*set_input_state)(InputState) = nullptr;
    void (*init)() = nullptr;
    void (*deinit)() = nullptr;
    bool (*load_game)(const GameInfo*) = nullptr;
    void (*unload_game)() = nullptr;
    void (*run)() = nullptr;
    void (*get_system_av_info)(AVInfo*) = nullptr;
    size_t (*serialize_size)() = nullptr;
    bool (*serialize)(void*, size_t) = nullptr;
    bool (*unserialize)(const void*, size_t) = nullptr;
    void* (*get_memory_data)(unsigned) = nullptr;
    size_t (*get_memory_size)(unsigned) = nullptr;
    void (*set_controller_port_device)(unsigned, unsigned) = nullptr;
};
Api api;
void* lib = nullptr;
std::mutex coreMutex, audioMutex;
std::vector<uint8_t> romBytes;
std::string gamePath, directory, lastError;
bool initialized = false, loaded = false;
unsigned pixelFormat = 0;
unsigned width = 256, height = 224;
double nominalFps = 60;
std::vector<jint> image(512*512, 0xff000000);
std::atomic<unsigned> pad{0};
desert::AudioRing<32768> audioRing;
desert::RamTrace trace;
uint64_t framesRun=0, videoCalls=0, audioPairs=0;

void audioSample(int16_t a, int16_t b) {
    std::lock_guard<std::mutex> l(audioMutex);
    audioRing.push(a,b);
    ++audioPairs;
}
size_t audioBatch(const int16_t* s, size_t n) {
    if (!s) return n;
    std::lock_guard<std::mutex> l(audioMutex);
    const auto count=std::min(n,size_t(65536));
    for (size_t i=0;i<count;++i) audioRing.push(s[2*i],s[2*i+1]);
    audioPairs += count;
    return n;
}
void video(const void* bytes, unsigned w, unsigned h, size_t pitch) {
    if (!bytes || reinterpret_cast<intptr_t>(bytes)==-1 || w==0 || h==0 || w>512 || h>512) return;
    width=w; height=h;
    ++videoCalls;
    const auto* base=static_cast<const uint8_t*>(bytes);
    for (unsigned y=0;y<h;++y) {
        const auto* row=base+pitch*y;
        for (unsigned x=0;x<w;++x) {
            uint32_t rgb;
            if (pixelFormat==1) {
                uint32_t p; std::memcpy(&p,row+4*x,4); rgb=p&0xffffff;
            } else {
                uint16_t p; std::memcpy(&p,row+2*x,2);
                if (pixelFormat==2) {
                    unsigned r=(p>>11)&31,g=(p>>5)&63,b=p&31;
                    rgb=((r<<3|r>>2)<<16)|((g<<2|g>>4)<<8)|(b<<3|b>>2);
                } else {
                    unsigned r=(p>>10)&31,g=(p>>5)&31,b=p&31;
                    rgb=((r<<3|r>>2)<<16)|((g<<3|g>>2)<<8)|(b<<3|b>>2);
                }
            }
            image[static_cast<size_t>(y)*w+x]=static_cast<jint>(0xff000000u|rgb);
        }
    }
}
bool environment(unsigned cmd, void* data) {
    switch(cmd) {
        case 9:  // GET_SYSTEM_DIRECTORY
        case 31: // GET_SAVE_DIRECTORY
            if (!data) return false;
            *static_cast<const char**>(data)=directory.c_str(); return true;
        case 10: // SET_PIXEL_FORMAT
            if (!data || *static_cast<unsigned*>(data)>2) return false;
            pixelFormat=*static_cast<unsigned*>(data); return true;
        case 3: // GET_CAN_DUPE
            if (!data) return false;
            *static_cast<bool*>(data)=true; return true;
        case 15: // GET_VARIABLE
            if (data) static_cast<Variable*>(data)->value=nullptr;
            return false;
        case 17: // GET_VARIABLE_UPDATE
            if (data) *static_cast<bool*>(data)=false;
            return data!=nullptr;
        case (51|0x10000): // GET_INPUT_BITMASKS
            return true;
        case 52: // GET_CORE_OPTIONS_VERSION
            if (data) *static_cast<unsigned*>(data)=0;
            return data!=nullptr;
        case 8:  // SET_PERFORMANCE_LEVEL
        case 11: // SET_INPUT_DESCRIPTORS
        case 16: // SET_VARIABLES
        case 32: // SET_SYSTEM_AV_INFO
            return true;
        default: return false;
    }
}
void inputPoll() {}
int16_t inputState(unsigned port,unsigned device,unsigned,unsigned id) {
    if (port!=0 || (device & 0xff)!=1) return 0;
    const unsigned state=pad.load(std::memory_order_relaxed);
    if (id==256) return static_cast<int16_t>(state);
    return id<16 && ((state >> id)&1) ? 1 : 0;
}
template <typename T> bool lookup(T& fn,const char* name) {
    fn=reinterpret_cast<T>(dlsym(lib,name));
    if (!fn) lastError=std::string("Símbolo ausente: ")+name;
    return fn!=nullptr;
}
bool resolve() {
    return lookup(api.set_environment,"retro_set_environment")
      && lookup(api.set_video_refresh,"retro_set_video_refresh")
      && lookup(api.set_audio_sample,"retro_set_audio_sample")
      && lookup(api.set_audio_sample_batch,"retro_set_audio_sample_batch")
      && lookup(api.set_input_poll,"retro_set_input_poll")
      && lookup(api.set_input_state,"retro_set_input_state")
      && lookup(api.init,"retro_init")
      && lookup(api.deinit,"retro_deinit")
      && lookup(api.load_game,"retro_load_game")
      && lookup(api.unload_game,"retro_unload_game")
      && lookup(api.run,"retro_run")
      && lookup(api.get_system_av_info,"retro_get_system_av_info")
      && lookup(api.serialize_size,"retro_serialize_size")
      && lookup(api.serialize,"retro_serialize")
      && lookup(api.unserialize,"retro_unserialize")
      && lookup(api.get_memory_data,"retro_get_memory_data")
      && lookup(api.get_memory_size,"retro_get_memory_size")
      && lookup(api.set_controller_port_device,"retro_set_controller_port_device");
}
void clean() {
    if (loaded && api.unload_game) api.unload_game();
    if (initialized && api.deinit) api.deinit();
    loaded=false; initialized=false;
    if (lib) { dlclose(lib); lib=nullptr; }
    api=Api{}; romBytes.clear(); trace.clear();
    framesRun=videoCalls=audioPairs=0;
    pad.store(0); width=256; height=224; nominalFps=60;
    std::lock_guard<std::mutex> lock(audioMutex);
    audioRing.clear();
}
std::string fromJava(JNIEnv* env,jstring s) {
    if (!s) return {};
    const char* data=env->GetStringUTFChars(s,nullptr);
    if (!data) return {};
    std::string text(data);
    env->ReleaseStringUTFChars(s,data);
    return text;
}
jbyteArray javaBytes(JNIEnv* env,const uint8_t* src,size_t n) {
    if (n==0 || n>32u*1024u*1024u) return nullptr;
    auto array=env->NewByteArray(static_cast<jsize>(n));
    if (array) env->SetByteArrayRegion(array,0,static_cast<jsize>(n),reinterpret_cast<const jbyte*>(src));
    return array;
}
}
extern "C" JNIEXPORT jdouble JNICALL
Java_br_com_desertstrike_NativeCore_start(JNIEnv* env,jobject,jstring path,jstring files,jbyteArray bytes) {
    std::lock_guard<std::mutex> lock(coreMutex);
    clean(); lastError.clear();
    if (!bytes) { lastError="ROM não fornecida"; return 0; }
    auto n=env->GetArrayLength(bytes);
    if (n<=0 || n>16*1024*1024) { lastError="Tamanho da ROM inválido"; return 0; }
    romBytes.resize(n);
    env->GetByteArrayRegion(bytes,0,n,reinterpret_cast<jbyte*>(romBytes.data()));
    directory=fromJava(env,files);
    gamePath=directory+"/loaded.sfc";
    const std::string library=fromJava(env,path);
    lib=dlopen(library.c_str(),RTLD_NOW|RTLD_LOCAL);
    if (!lib) {
        const char* error=dlerror();
        lastError=error?error:"Falha ao carregar biblioteca";
        clean(); return 0;
    }
    if (!resolve()) { clean(); return 0; }
    api.set_environment(environment);
    api.set_video_refresh(video);
    api.set_audio_sample(audioSample);
    api.set_audio_sample_batch(audioBatch);
    api.set_input_poll(inputPoll);
    api.set_input_state(inputState);
    api.init(); initialized=true;
    GameInfo info{gamePath.c_str(),romBytes.data(),romBytes.size(),nullptr};
    pixelFormat=0;
    if (!api.load_game(&info)) { lastError="Núcleo recusou a ROM"; clean(); return 0; }
    loaded=true;
    api.set_controller_port_device(0,1);
    AVInfo av{};
    api.get_system_av_info(&av);
    if (av.timing.fps>=30 && av.timing.fps<=120) nominalFps=av.timing.fps;
    return av.timing.sample_rate>4000 && av.timing.sample_rate<192000 ? av.timing.sample_rate : 32040.0;
}
extern "C" JNIEXPORT jstring JNICALL
Java_br_com_desertstrike_NativeCore_lastError(JNIEnv* env,jobject) {
    std::lock_guard<std::mutex> lock(coreMutex);
    return env->NewStringUTF(lastError.c_str());
}
extern "C" JNIEXPORT jdouble JNICALL
Java_br_com_desertstrike_NativeCore_fps(JNIEnv*,jobject) {
    std::lock_guard<std::mutex> lock(coreMutex);
    return nominalFps;
}
extern "C" JNIEXPORT void JNICALL
Java_br_com_desertstrike_NativeCore_stop(JNIEnv*,jobject) {
    std::lock_guard<std::mutex> lock(coreMutex);
    clean();
}
extern "C" JNIEXPORT jstring JNICALL
Java_br_com_desertstrike_NativeCore_stats(JNIEnv* env,jobject) {
    std::lock_guard<std::mutex> coreLock(coreMutex);
    std::lock_guard<std::mutex> audioLock(audioMutex);
    const std::string json=std::string("{\"loaded\":")+(loaded?"true":"false")+
        ",\"frames\":"+std::to_string(framesRun)+
        ",\"video_callbacks\":"+std::to_string(videoCalls)+
        ",\"audio_pairs\":"+std::to_string(audioPairs)+
        ",\"pending_audio_samples\":"+std::to_string(audioRing.pending())+
        ",\"video_width\":"+std::to_string(width)+
        ",\"video_height\":"+std::to_string(height)+
        ",\"trace_frames\":"+std::to_string(trace.count())+
        ",\"trace_active\":"+(trace.active()?"true":"false")+"}";
    return env->NewStringUTF(json.c_str());
}
extern "C" JNIEXPORT jint JNICALL
Java_br_com_desertstrike_NativeCore_frame(JNIEnv* env,jobject,jintArray output) {
    std::lock_guard<std::mutex> lock(coreMutex);
    if (!loaded || !output) return 0;
    api.run();
    ++framesRun;
    if (trace.active()) trace.capture(api.get_memory_data(2),api.get_memory_size(2),
                                     static_cast<uint16_t>(pad.load()));
    const auto count=width*height;
    if (static_cast<unsigned>(env->GetArrayLength(output))<count) return 0;
    env->SetIntArrayRegion(output,0,static_cast<jsize>(count),image.data());
    return static_cast<jint>((height<<16)|width);
}
extern "C" JNIEXPORT void JNICALL
Java_br_com_desertstrike_NativeCore_input(JNIEnv*,jobject,jint bits) {
    pad.store(static_cast<unsigned>(bits)&0xffffu,std::memory_order_relaxed);
}
extern "C" JNIEXPORT jint JNICALL
Java_br_com_desertstrike_NativeCore_drainAudio(JNIEnv* env,jobject,jshortArray output) {
    if (!output) return 0;
    std::vector<int16_t> samples;
    {
        std::lock_guard<std::mutex> lock(audioMutex);
        const auto n=std::min(static_cast<size_t>(env->GetArrayLength(output)),audioRing.pending())&~size_t(1);
        samples.resize(n);
        samples.resize(audioRing.drain(samples.data(),samples.size()));
    }
    if (!samples.empty()) env->SetShortArrayRegion(output,0,static_cast<jsize>(samples.size()),samples.data());
    return static_cast<jint>(samples.size());
}
extern "C" JNIEXPORT jbyteArray JNICALL
Java_br_com_desertstrike_NativeCore_saveState(JNIEnv* env,jobject) {
    std::lock_guard<std::mutex> lock(coreMutex);
    if (!loaded) return nullptr;
    const auto n=api.serialize_size();
    if (n==0 || n>32u*1024u*1024u) return nullptr;
    std::vector<uint8_t> bytes(n);
    return api.serialize(bytes.data(),n)?javaBytes(env,bytes.data(),n):nullptr;
}
extern "C" JNIEXPORT jboolean JNICALL
Java_br_com_desertstrike_NativeCore_loadState(JNIEnv* env,jobject,jbyteArray state) {
    std::lock_guard<std::mutex> lock(coreMutex);
    if (!loaded || !state) return JNI_FALSE;
    const auto n=static_cast<size_t>(env->GetArrayLength(state));
    if (n!=api.serialize_size() || n==0 || n>32u*1024u*1024u) return JNI_FALSE;
    std::vector<uint8_t> bytes(n);
    env->GetByteArrayRegion(state,0,static_cast<jsize>(n),reinterpret_cast<jbyte*>(bytes.data()));
    return api.unserialize(bytes.data(),n)?JNI_TRUE:JNI_FALSE;
}
extern "C" JNIEXPORT jbyteArray JNICALL
Java_br_com_desertstrike_NativeCore_saveRam(JNIEnv* env,jobject) {
    std::lock_guard<std::mutex> lock(coreMutex);
    if (!loaded) return nullptr;
    auto* data=static_cast<uint8_t*>(api.get_memory_data(0));
    const auto n=api.get_memory_size(0);
    return data && n<=512*1024?javaBytes(env,data,n):nullptr;
}
extern "C" JNIEXPORT jboolean JNICALL
Java_br_com_desertstrike_NativeCore_loadRam(JNIEnv* env,jobject,jbyteArray data) {
    std::lock_guard<std::mutex> lock(coreMutex);
    if (!loaded || !data) return JNI_FALSE;
    auto* dest=static_cast<jbyte*>(api.get_memory_data(0));
    const auto n=api.get_memory_size(0);
    if (!dest || n!=static_cast<size_t>(env->GetArrayLength(data))) return JNI_FALSE;
    env->GetByteArrayRegion(data,0,static_cast<jsize>(n),dest);
    return JNI_TRUE;
}
extern "C" JNIEXPORT jboolean JNICALL
Java_br_com_desertstrike_NativeCore_traceStart(JNIEnv*,jobject) {
    std::lock_guard<std::mutex> lock(coreMutex);
    return loaded && trace.begin(api.get_memory_data(2),api.get_memory_size(2))?JNI_TRUE:JNI_FALSE;
}
extern "C" JNIEXPORT jstring JNICALL
Java_br_com_desertstrike_NativeCore_traceStop(JNIEnv* env,jobject) {
    std::lock_guard<std::mutex> lock(coreMutex);
    if (!trace.count()) { trace.clear(); return nullptr; }
    const std::string json=trace.json();
    trace.clear();
    return env->NewStringUTF(json.c_str());
}
