#include "flight_engine.hpp"
#include <jni.h>
#include <mutex>
#include <string>
namespace {
std::mutex mutex;
romnative::FlightEngine engine;
}
extern "C" JNIEXPORT jboolean JNICALL
Java_br_com_rom2native_NativeEngine_importRom(JNIEnv* env,jobject,jbyteArray data) {
    if (!data) return JNI_FALSE;
    const auto len=env->GetArrayLength(data);
    if(len!=1024*1024) return JNI_FALSE;
    auto* bytes=env->GetByteArrayElements(data,nullptr);
    if(!bytes) return JNI_FALSE;
    std::lock_guard<std::mutex> lock(mutex);
    const bool loaded=engine.load(reinterpret_cast<const uint8_t*>(bytes),size_t(len));
    env->ReleaseByteArrayElements(data,bytes,JNI_ABORT);
    return loaded?JNI_TRUE:JNI_FALSE;
}
extern "C" JNIEXPORT void JNICALL
Java_br_com_rom2native_NativeEngine_step(JNIEnv*,jobject,jint mask,jfloat dt) {
    std::lock_guard<std::mutex> lock(mutex);
    engine.step(static_cast<uint32_t>(mask),dt);
}
extern "C" JNIEXPORT void JNICALL
Java_br_com_rom2native_NativeEngine_draw(JNIEnv* env,jobject,jintArray target) {
    if(!target || env->GetArrayLength(target)<romnative::WIDTH*romnative::HEIGHT)return;
    std::array<uint32_t,romnative::WIDTH*romnative::HEIGHT> image{};
    {std::lock_guard<std::mutex> lock(mutex);engine.render(image.data(),image.size());}
    env->SetIntArrayRegion(target,0,static_cast<jsize>(image.size()),
        reinterpret_cast<const jint*>(image.data()));
}
extern "C" JNIEXPORT jboolean JNICALL
Java_br_com_rom2native_NativeEngine_setHelicopterSprite(
        JNIEnv* env,jobject,jintArray data,jint width,jint height) {
    if (!data || width<1 || height<1 || width>128 || height>128 ||
         env->GetArrayLength(data)!=width*height) return JNI_FALSE;
    std::vector<jint> pixels(static_cast<size_t>(width)*height);
    env->GetIntArrayRegion(data,0,static_cast<jsize>(pixels.size()),pixels.data());
    if (env->ExceptionCheck()) return JNI_FALSE;
    std::lock_guard<std::mutex> lock(mutex);
    return engine.setHelicopterSprite(reinterpret_cast<const uint32_t*>(pixels.data()),
        pixels.size(),width,height) ? JNI_TRUE : JNI_FALSE;
}

extern "C" JNIEXPORT jboolean JNICALL
Java_br_com_rom2native_NativeEngine_setHelicopterAtlas(
        JNIEnv* env,jobject,jintArray data,jint width,jint height,jint frames){
    if(!data || (frames!=1 && frames!=8) || width<1 || height<1 ||
       height>128 || width>frames*128 || width%frames ||
       env->GetArrayLength(data)!=static_cast<jsize>(width*height))
       return JNI_FALSE;
    std::vector<jint> pixels(static_cast<size_t>(width)*height);
    env->GetIntArrayRegion(data,0,static_cast<jsize>(pixels.size()),pixels.data());
    if(env->ExceptionCheck())return JNI_FALSE;
    std::lock_guard<std::mutex> lock(mutex);
    return engine.setHelicopterAtlas(reinterpret_cast<const uint32_t*>(pixels.data()),
        pixels.size(),width,height,frames)?JNI_TRUE:JNI_FALSE;
}
extern "C" JNIEXPORT jboolean JNICALL
Java_br_com_rom2native_NativeEngine_setSceneImage(
        JNIEnv* env,jobject,jintArray data,jint width,jint height) {
    if (!data || width!=romnative::WIDTH || height!=romnative::HEIGHT ||
        env->GetArrayLength(data)!=romnative::WIDTH*romnative::HEIGHT) return JNI_FALSE;
    std::vector<jint> pixels(static_cast<size_t>(width)*height);
    env->GetIntArrayRegion(data,0,static_cast<jsize>(pixels.size()),pixels.data());
    if(env->ExceptionCheck())return JNI_FALSE;
    std::lock_guard<std::mutex> lock(mutex);
    return engine.setSceneImage(reinterpret_cast<const uint32_t*>(pixels.data()),
        pixels.size(),width,height)?JNI_TRUE:JNI_FALSE;
}
extern "C" JNIEXPORT void JNICALL
Java_br_com_rom2native_NativeEngine_clearSceneImage(JNIEnv*,jobject) {
    std::lock_guard<std::mutex> lock(mutex);
    engine.clearScene();
}
extern "C" JNIEXPORT jboolean JNICALL
Java_br_com_rom2native_NativeEngine_configureMission(JNIEnv* env,jobject,
        jintArray targetData,jint count){
    if(!targetData || count<1 || count>romnative::CombatMission::MAX_TARGETS ||
       env->GetArrayLength(targetData)!=count*5)return JNI_FALSE;
    std::vector<jint> values(static_cast<size_t>(count)*5);
    env->GetIntArrayRegion(targetData,0,static_cast<jsize>(values.size()),values.data());
    if(env->ExceptionCheck())return JNI_FALSE;
    std::vector<romnative::CombatMission::TargetSpec> specs;
    specs.reserve(static_cast<size_t>(count));
    for(int i=0;i<count;++i){
        const int offset=i*5;
        specs.push_back({static_cast<float>(values[offset]),
                         static_cast<float>(values[offset+1]),
                         values[offset+2],values[offset+3],values[offset+4]});
    }
    std::lock_guard<std::mutex> lock(mutex);
    return engine.configureMission(specs)?JNI_TRUE:JNI_FALSE;
}
extern "C" JNIEXPORT void JNICALL
Java_br_com_rom2native_NativeEngine_defaultMission(JNIEnv*,jobject){
    std::lock_guard<std::mutex> lock(mutex);
    engine.useDefaultMission();
}
extern "C" JNIEXPORT void JNICALL
Java_br_com_rom2native_NativeEngine_restartMission(JNIEnv*,jobject) {
    std::lock_guard<std::mutex> lock(mutex);
    engine.restartMission();
}

extern "C" JNIEXPORT jintArray JNICALL
Java_br_com_rom2native_NativeEngine_missionStats(JNIEnv* env,jobject) {
    std::array<jint,4> stats{};
    {
        std::lock_guard<std::mutex> lock(mutex);
        const auto& mission=engine.mission();
        stats={mission.health(),mission.destroyed(),
               mission.total(),
               static_cast<jint>(mission.state())};
    }
    auto result=env->NewIntArray(4);
    if(result)env->SetIntArrayRegion(result,0,4,stats.data());
    return result;
}

extern "C" JNIEXPORT jstring JNICALL
Java_br_com_rom2native_NativeEngine_status(JNIEnv* env,jobject) {
    std::lock_guard<std::mutex> lock(mutex);
    const auto s=std::string(engine.ready()?"MOTOR NATIVO":"SEM ROM")+
       " | frames="+std::to_string(engine.frames())+
       " | tiros="+std::to_string(engine.shotCount())+
       " | sprite="+(engine.hasHelicopterSprite()?"personalizado":"provisorio")+
       " | angulo="+std::to_string(engine.heading())+
       " | frames_sprite="+std::to_string(engine.spriteFrames())+
       " | cenario="+(engine.hasScene()?"personalizado":"provisorio")+
       " | HP="+std::to_string(engine.mission().health())+
       " | destruidos="+std::to_string(engine.mission().destroyed())+
       "/"+std::to_string(engine.mission().total());
    return env->NewStringUTF(s.c_str());
}
